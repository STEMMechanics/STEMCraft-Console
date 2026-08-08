import threading

from datetime import datetime

from .backup_manager import (
    create_backup,
)

from .database import (
    SessionLocal,
)

from .models import (
    BackupJob,
    Server,
)

from .processes import (
    send_command,
    server_status,
    wait_for_console_message,
)


def start_backup_job(
    job_id: int,
):
    thread = threading.Thread(
        target=run_backup_job,
        args=(job_id,),
        daemon=True,
        name=f"backup-job-{job_id}",
    )

    thread.start()


def run_backup_job(
    job_id: int,
):
    db = SessionLocal()

    job = None

    running = False
    saves_disabled = False

    try:

        job = db.get(
            BackupJob,
            job_id,
        )

        if not job:
            return


        server = db.get(
            Server,
            job.server_id,
        )

        if not server:

            job.status = "failed"
            job.message = (
                "Server not found"
            )
            job.finished_at = (
                datetime.utcnow()
            )

            db.commit()

            return


        job.status = "saving"
        job.progress = 0
        job.message = (
            "Preparing world save"
        )
        job.started_at = (
            datetime.utcnow()
        )

        db.commit()


        running = server_status(
            server.id
        ).get(
            "running",
            False,
        )


        if running:

            send_command(
                server.id,
                "save-all flush",
            )


            saved = (
                wait_for_console_message(
                    server.id,
                    [
                        "Saved the game",
                        "Saved the world",
                        "Saving complete",
                    ],
                    timeout=15,
                )
            )

            if not saved:

                raise RuntimeError(
                    "Timed out waiting "
                    "for Minecraft to "
                    "finish saving."
                )


            send_command(
                server.id,
                "save-off",
            )

            saves_disabled = True


        job.status = "archiving"
        job.progress = 0
        job.message = (
            "Creating backup archive"
        )

        db.commit()


        def update_progress(
            value: int,
        ):

            # Refresh in case another
            # session modified the row.
            current_job = db.get(
                BackupJob,
                job_id,
            )

            if not current_job:
                return

            current_job.progress = (
                max(
                    0,
                    min(
                        100,
                        int(value),
                    ),
                )
            )

            current_job.message = (
                "Creating backup archive"
            )

            db.commit()


        result = create_backup(
            server,
            job.label,
            progress_callback=
                update_progress,
        )


        job = db.get(
            BackupJob,
            job_id,
        )

        if not job:
            return


        job.filename = result[
            "filename"
        ]

        job.progress = 100
        job.status = "complete"

        job.message = (
            "Backup complete"
        )

        job.finished_at = (
            datetime.utcnow()
        )

        db.commit()


    except Exception as error:

        if job is None:

            job = db.get(
                BackupJob,
                job_id,
            )


        if job:

            job.status = "failed"

            job.message = (
                str(error)
            )

            job.finished_at = (
                datetime.utcnow()
            )

            db.commit()


    finally:

        if (
            running
            and saves_disabled
        ):

            try:

                server = db.get(
                    Server,
                    job.server_id
                    if job
                    else None,
                )

                if server:

                    send_command(
                        server.id,
                        "save-on",
                    )

            except Exception:
                pass


        db.close()