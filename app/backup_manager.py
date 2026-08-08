import shutil
import zipfile

from datetime import datetime
from pathlib import Path


def backup_directory(server) -> Path:
    directory = (
        Path(server.directory)
        / "backups"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def safe_backup_path(
    server,
    filename: str,
) -> Path:

    directory = (
        backup_directory(server)
        .resolve()
    )

    path = (
        directory
        / Path(filename).name
    ).resolve()

    if path.parent != directory:
        raise ValueError(
            "Invalid backup path"
        )

    if path.suffix.lower() != ".zip":
        raise ValueError(
            "Invalid backup file"
        )

    return path


def format_size(
    size: int,
) -> str:

    if size < 1024:
        return f"{size} B"

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"

    if size < 1024 * 1024 * 1024:
        return (
            f"{size / 1024 / 1024:.1f} MB"
        )

    return (
        f"{size / 1024 / 1024 / 1024:.1f} GB"
    )


def list_backups(server) -> list[dict]:

    directory = backup_directory(
        server
    )

    backups = []

    for path in directory.glob(
        "*.zip"
    ):

        try:
            stat = path.stat()

        except OSError:
            continue

        created = datetime.fromtimestamp(
            stat.st_mtime
        )

        backups.append({
            "filename":
                path.name,

            "size":
                stat.st_size,

            "size_display":
                format_size(
                    stat.st_size
                ),

            "created":
                created.isoformat(),

            "created_display":
                created.strftime(
                    "%d %b %Y, %I:%M %p"
                ),
        })

    backups.sort(
        key=lambda item:
            item["created"],
        reverse=True,
    )

    return backups


def create_backup(
    server,
    label: str | None = None,
    progress_callback=None,
) -> dict:

    root = Path(
        server.directory
    ).resolve()

    backups = backup_directory(
        server
    ).resolve()

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    safe_label = ""

    if label:

        safe_label = "".join(
            character
            for character in label.strip()
            if (
                character.isalnum()
                or character in (
                    "-",
                    "_",
                )
            )
        )

    filename = timestamp

    if safe_label:
        filename += (
            "-" + safe_label
        )

    filename += ".zip"

    destination = (
        backups / filename
    )


    files = []

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        # Never back up the backups
        # directory itself.
        if (
            path == backups
            or backups in path.parents
        ):
            continue

        files.append(
            path
        )


    total_bytes = 0

    for path in files:

        try:
            total_bytes += (
                path.stat().st_size
            )

        except OSError:
            pass


    processed_bytes = 0

    last_progress = -1


    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:

        for path in files:

            try:

                size = (
                    path.stat().st_size
                )

                archive.write(
                    path,
                    path.relative_to(root),
                )

                processed_bytes += size


            except (
                FileNotFoundError,
                PermissionError,
                OSError,
            ):
                # A file may disappear while
                # the server is running.
                continue


            if progress_callback:

                if total_bytes > 0:

                    progress = int(
                        processed_bytes
                        / total_bytes
                        * 100
                    )

                else:

                    progress = 100


                # Don't hammer SQLite with
                # identical progress updates.
                if progress != last_progress:

                    progress_callback(
                        progress
                    )

                    last_progress = progress


    if progress_callback:
        progress_callback(100)


    stat = destination.stat()


    return {
        "filename":
            destination.name,

        "size":
            stat.st_size,

        "size_display":
            format_size(
                stat.st_size
            ),
    }

def delete_backup(
    server,
    filename: str,
):

    path = safe_backup_path(
        server,
        filename,
    )

    if not path.exists():
        raise FileNotFoundError(
            "Backup not found"
        )

    path.unlink()


def restore_backup(
    server,
    filename: str,
):

    archive_path = safe_backup_path(
        server,
        filename,
    )

    if not archive_path.exists():
        raise FileNotFoundError(
            "Backup not found"
        )

    root = Path(
        server.directory
    ).resolve()

    backups = backup_directory(
        server
    ).resolve()

    temp = (
        root.parent
        / f".{root.name}-restore"
    )

    if temp.exists():
        shutil.rmtree(
            temp
        )

    temp.mkdir(
        parents=True
    )

    try:

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            for member in archive.infolist():

                member_path = (
                    temp / member.filename
                ).resolve()

                try:
                    member_path.relative_to(
                        temp.resolve()
                    )

                except ValueError:
                    raise ValueError(
                        "Backup contains unsafe paths"
                    )

            archive.extractall(
                temp
            )


        for item in root.iterdir():

            if item.resolve() == backups:
                continue

            if item.is_dir():
                shutil.rmtree(
                    item
                )

            else:
                item.unlink()


        for item in temp.iterdir():

            destination = (
                root / item.name
            )

            shutil.move(
                str(item),
                str(destination),
            )

    finally:

        shutil.rmtree(
            temp,
            ignore_errors=True,
        )