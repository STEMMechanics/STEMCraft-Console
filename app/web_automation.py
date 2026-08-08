from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import ScheduledTask, ServerMetric, TaskRun
from .web_servers import get_accessible_server


router = APIRouter()


def _task_json(task):
    return {
        "id": task.id, "name": task.name, "task_type": task.task_type,
        "command": task.command, "interval_minutes": task.interval_minutes,
        "retention_count": task.retention_count, "enabled": task.enabled,
        "next_run_at": task.next_run_at.isoformat(),
        "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
    }


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
    if not server or user.role != "admin":
        return JSONResponse({"error": "Admin required"}, status_code=403)
    data = await request.json()
    task_type = str(data.get("task_type", ""))
    name = str(data.get("name", "")).strip()
    command = str(data.get("command", "")).strip() or None
    try:
        interval = int(data.get("interval_minutes", 0))
        retention = int(data["retention_count"]) if data.get("retention_count") else None
    except (TypeError, ValueError):
        return JSONResponse({"error": "Invalid interval or retention"}, status_code=400)
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
        next_run_at=datetime.utcnow() + timedelta(minutes=interval),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_json(task)


@router.delete("/api/web/servers/{server_id}/schedules/{task_id}")
def delete_schedule(server_id: int, task_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or user.role != "admin":
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
