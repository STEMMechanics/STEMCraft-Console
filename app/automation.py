"""Durable scheduled tasks and historical server metrics."""

import os
import threading
import logging
from datetime import datetime, timedelta

import psutil

from .backup_jobs import run_backup_job
from .backup_manager import list_backups, delete_backup
from .database import SessionLocal
from .models import BackupJob, ScheduledTask, Server, ServerMetric, TaskRun
from .player_manager import get_online_players
from .processes import register_server, send_command, server_process_stats, server_status


_stop = threading.Event()
_thread: threading.Thread | None = None
logger = logging.getLogger(__name__)
POLL_SECONDS = max(5, int(os.getenv("STEMCRAFT_AUTOMATION_POLL_SECONDS", "30")))
METRIC_SECONDS = max(15, int(os.getenv("STEMCRAFT_METRIC_INTERVAL_SECONDS", "60")))
METRIC_RETENTION_DAYS = max(1, int(os.getenv("STEMCRAFT_METRIC_RETENTION_DAYS", "30")))


def enforce_backup_retention(server, keep: int | None) -> None:
    if not keep or keep < 1:
        return
    for backup in list_backups(server)[keep:]:
        delete_backup(server, backup["filename"])


def execute_task(task_id: int) -> None:
    db = SessionLocal()
    run = None
    try:
        task = db.get(ScheduledTask, task_id)
        if not task or not task.enabled:
            return
        server = db.get(Server, task.server_id)
        if not server:
            return
        register_server(server)
        now = datetime.utcnow()
        task.last_run_at = now
        task.next_run_at = now + timedelta(minutes=task.interval_minutes)
        run = TaskRun(
            task_id=task.id, server_id=server.id, task_type=task.task_type,
            status="running", started_at=now,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        if task.task_type == "command":
            if not task.command:
                raise RuntimeError("Scheduled command is empty")
            send_command(server.id, task.command)
            run.detail = f"Sent: {task.command}"
        elif task.task_type == "backup":
            existing = db.query(BackupJob).filter(
                BackupJob.server_id == server.id,
                BackupJob.status.in_(["queued", "saving", "archiving"]),
            ).first()
            if existing:
                raise RuntimeError("A backup is already running")
            job = BackupJob(
                server_id=server.id, label=task.name,
                status="queued", progress=0, message="Scheduled",
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            run_backup_job(job.id)
            db.refresh(job)
            if job.status != "complete":
                raise RuntimeError(job.message or "Backup failed")
            enforce_backup_retention(server, task.retention_count)
            run.detail = f"Created {job.filename}"
        else:
            raise RuntimeError("Unsupported scheduled task type")

        run.status = "complete"
        run.finished_at = datetime.utcnow()
        db.commit()
    except Exception as error:
        if run:
            run.status = "failed"
            run.detail = str(error)[:1000]
            run.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def collect_metrics() -> None:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        for server in db.query(Server).filter(Server.enabled.is_(True)).all():
            register_server(server)
            status = server_status(server.id)
            stats = server_process_stats(server.id)
            uptime = None
            pid = status.get("pid")
            if status.get("running") and pid:
                try:
                    uptime = max(0, int(now.timestamp() - psutil.Process(pid).create_time()))
                except psutil.Error:
                    pass
            db.add(ServerMetric(
                server_id=server.id,
                recorded_at=now,
                running=bool(status.get("running")),
                cpu_percent=int(round(stats.get("cpu_percent", 0))),
                memory_bytes=int(stats.get("memory_used", 0)),
                player_count=len(get_online_players(server.id)),
                uptime_seconds=uptime,
            ))
        cutoff = now - timedelta(days=METRIC_RETENTION_DAYS)
        db.query(ServerMetric).filter(ServerMetric.recorded_at < cutoff).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def run_due_tasks() -> None:
    db = SessionLocal()
    try:
        due = [task.id for task in db.query(ScheduledTask).filter(
            ScheduledTask.enabled.is_(True),
            ScheduledTask.next_run_at <= datetime.utcnow(),
        ).all()]
    finally:
        db.close()
    for task_id in due:
        execute_task(task_id)


def _automation_loop() -> None:
    last_metrics = 0.0
    while not _stop.wait(POLL_SECONDS):
        try:
            run_due_tasks()
        except Exception:
            logger.exception("Scheduled task polling failed")
        now = datetime.now().timestamp()
        if now - last_metrics >= METRIC_SECONDS:
            try:
                collect_metrics()
            except Exception:
                logger.exception("Historical metric collection failed")
            last_metrics = now


def start_automation() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    collect_metrics()
    _thread = threading.Thread(target=_automation_loop, name="automation", daemon=True)
    _thread.start()


def stop_automation() -> None:
    _stop.set()
    if _thread:
        _thread.join(timeout=5)
