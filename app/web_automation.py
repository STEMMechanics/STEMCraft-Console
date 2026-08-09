from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import ScheduledTask, ServerMetric, TaskRun
from .web_servers import get_accessible_server
from .permissions import has_permission
from .automation import next_task_run, validate_cron_expression
from .web_context import build_web_context
from .web_render import render_page
from .config import SCHEDULE_TIMEZONE_NAME


router = APIRouter()


def _task_json(task):
    return {
        "id": task.id, "name": task.name, "task_type": task.task_type,
        "command": task.command, "interval_minutes": task.interval_minutes,
        "frequency": task.frequency, "run_hour": task.run_hour,
        "run_weekday": task.run_weekday,
        "cron_expression": task.cron_expression,
        "retention_count": task.retention_count, "enabled": task.enabled,
        "next_run_at": task.next_run_at.isoformat(),
        "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
    }


@router.get("/servers/{server_id}/scheduling", response_class=HTMLResponse)
def automation_page(server_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return RedirectResponse("/login")
    if not server or not (
        has_permission(user, "automation.manage")
        or has_permission(user, "backups.view")
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    context = build_web_context(db, user, active_server=server)
    context.update({
        "server": server,
        "page_title": "Scheduling",
        "active_page": "scheduling",
        "schedule_timezone": SCHEDULE_TIMEZONE_NAME,
    })
    return render_page(request, "server_automation.html", "partials/server_automation.html", context)


@router.get("/servers/{server_id}/automation")
def old_automation_page(server_id: int):
    return RedirectResponse(f"/servers/{server_id}/scheduling", status_code=301)


@router.get("/api/web/servers/{server_id}/schedules")
def schedules(server_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server:
        return JSONResponse({"error": "Access denied"}, status_code=403)
    tasks = db.query(ScheduledTask).filter(ScheduledTask.server_id == server.id).order_by(ScheduledTask.name).all()
    runs = db.query(TaskRun).filter(TaskRun.server_id == server.id).order_by(TaskRun.id.desc()).limit(50).all()
    return {
        "tasks": [_task_json(task) for task in tasks],
        "runs": [{
            "id": run.id, "task_id": run.task_id, "task_type": run.task_type,
            "status": run.status, "detail": run.detail,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        } for run in runs],
    }


@router.post("/api/web/servers/{server_id}/schedules")
async def create_schedule(server_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, "automation.manage"):
        return JSONResponse({"error": "Admin required"}, status_code=403)
    data = await request.json()
    task_type = str(data.get("task_type", ""))
    name = str(data.get("name", "")).strip()
    command = str(data.get("command", "")).strip() or None
    frequency = str(data.get("frequency", "")).strip()
    cron_expression = str(data.get("cron_expression", "")).strip() or None
    try:
        interval = int(data.get("interval_minutes", 0) or 0)
        retention = int(data["retention_count"]) if data.get("retention_count") else None
        run_hour = int(data["run_hour"]) if data.get("run_hour") not in (None, "") else None
        run_weekday = int(data["run_weekday"]) if data.get("run_weekday") not in (None, "") else None
    except (TypeError, ValueError):
        return JSONResponse({"error": "Invalid interval or retention"}, status_code=400)
    if frequency in {"hourly", "daily", "weekly", "monthly", "custom"}:
        interval = {"hourly": 60, "daily": 1440, "weekly": 10080, "monthly": 43200, "custom": 1}[frequency]
    elif not frequency:
        frequency = None
    else:
        return JSONResponse({"error": "Choose a valid schedule"}, status_code=400)
    if frequency in {"daily", "weekly", "monthly"} and (run_hour is None or not 0 <= run_hour <= 23):
        return JSONResponse({"error": "Choose an hour from 0 to 23"}, status_code=400)
    if frequency == "weekly" and (run_weekday is None or not 0 <= run_weekday <= 6):
        return JSONResponse({"error": "Choose a day of the week"}, status_code=400)
    if frequency == "custom":
        try:
            validate_cron_expression(cron_expression or "")
        except (TypeError, ValueError) as error:
            return JSONResponse({"error": str(error)}, status_code=400)
    if task_type not in {"backup", "command"} or not name or interval < 1 or interval > 525600:
        return JSONResponse({"error": "Type, name and a positive interval are required"}, status_code=400)
    if task_type == "command" and not command:
        return JSONResponse({"error": "Command required"}, status_code=400)
    if task_type == "backup" and retention is not None and not 1 <= retention <= 10000:
        return JSONResponse({"error": "Retention must be between 1 and 10000"}, status_code=400)
    if command and (len(command) > 500 or "\n" in command or "\r" in command):
        return JSONResponse({"error": "Invalid command"}, status_code=400)
    task = ScheduledTask(
        server_id=server.id, task_type=task_type, name=name[:100], command=command,
        interval_minutes=interval, retention_count=retention, enabled=True,
        frequency=frequency, run_hour=run_hour, run_weekday=run_weekday,
        cron_expression=cron_expression,
        next_run_at=datetime.utcnow() + timedelta(minutes=interval),
    )
    task.next_run_at = next_task_run(task, datetime.utcnow())
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_json(task)


@router.delete("/api/web/servers/{server_id}/schedules/{task_id}")
def delete_schedule(server_id: int, task_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, "automation.manage"):
        return JSONResponse({"error": "Admin required"}, status_code=403)
    task = db.get(ScheduledTask, task_id)
    if not task or task.server_id != server.id:
        return JSONResponse({"error": "Schedule not found"}, status_code=404)
    # Keep the task row so its immutable execution audit remains available.
    task.enabled = False
    db.commit()
    return {"success": True}


@router.get("/api/web/servers/{server_id}/metrics")
def metrics(server_id: int, request: Request, hours: int = 24, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server:
        return JSONResponse({"error": "Access denied"}, status_code=403)
    hours = min(24 * 30, max(1, hours))
    rows = db.query(ServerMetric).filter(
        ServerMetric.server_id == server.id,
        ServerMetric.recorded_at >= datetime.utcnow() - timedelta(hours=hours),
    ).order_by(ServerMetric.recorded_at).limit(5000).all()
    return {"metrics": [{
        "recorded_at": row.recorded_at.isoformat(), "running": row.running,
        "cpu_percent": row.cpu_percent, "memory_bytes": row.memory_bytes,
        "player_count": row.player_count, "uptime_seconds": row.uptime_seconds,
    } for row in rows]}
