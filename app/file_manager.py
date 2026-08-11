import shutil
from datetime import datetime

from pathlib import Path


EDITABLE_EXTENSIONS = {
    ".txt",
    ".properties",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".conf",
    ".cfg",
    ".ini",
    ".md",
    ".log",
}


def server_root(server) -> Path:
    return Path(
        server.directory
    ).resolve()


def safe_path(
    server,
    relative_path: str = "",
) -> Path:

    root = server_root(server)

    requested = (
        root / relative_path
    ).resolve()

    try:
        requested.relative_to(root)

    except ValueError:
        raise ValueError(
            "Invalid path"
        )

    return requested


def relative_path(
    server,
    path: Path,
) -> str:

    return str(
        path.resolve().relative_to(
            server_root(server)
        )
    )


def format_size(
    size: int,
) -> str:

    if size < 1024:
        return f"{size} Bytes"

    if size < 1024 * 1024:
        return (
            f"{size / 1024:.1f} KB"
        )

    if size < 1024 * 1024 * 1024:
        return (
            f"{size / 1024 / 1024:.1f} MB"
        )

    return (
        f"{size / 1024 / 1024 / 1024:.1f} GB"
    )


def list_directory(
    server,
    relative: str = "",
):

    directory = safe_path(
        server,
        relative,
    )

    if not directory.exists():
        raise FileNotFoundError(
            "Directory not found"
        )

    if not directory.is_dir():
        raise ValueError(
            "Not a directory"
        )

    entries = []

    for item in directory.iterdir():

        try:
            stat = item.stat()

        except OSError:
            continue


        entries.append({
            "name":
                item.name,

            "path":
                relative_path(
                    server,
                    item,
                ),

            "is_dir":
                item.is_dir(),

            "modified":
                datetime.fromtimestamp(
                    stat.st_mtime
                ),

            "size":
                (
                    None
                    if item.is_dir()
                    else stat.st_size
                ),

            "size_display":
                (
                    ""
                    if item.is_dir()
                    else format_size(
                        stat.st_size
                    )
                ),

            "editable":
                (
                    item.is_file()
                    and item.suffix.lower()
                    in EDITABLE_EXTENSIONS
                ),
        })


    entries.sort(
        key=lambda item: (
            not item["is_dir"],
            item["name"].lower(),
        )
    )


    parent = None

    root = server_root(server)

    if directory != root:

        parent = relative_path(
            server,
            directory.parent,
        )


    return {
        "entries": entries,
        "current_path":
            relative_path(
                server,
                directory,
            ),

        "parent_path":
            parent,
    }


def read_text_file(
    server,
    relative: str,
):

    path = safe_path(
        server,
        relative,
    )

    if not path.is_file():
        raise FileNotFoundError(
            "File not found"
        )

    if (
        path.suffix.lower()
        not in EDITABLE_EXTENSIONS
    ):
        raise ValueError(
            "This file cannot be edited as text"
        )

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def write_text_file(
    server,
    relative: str,
    contents: str,
):

    path = safe_path(
        server,
        relative,
    )

    if not path.is_file():
        raise FileNotFoundError(
            "File not found"
        )

    if (
        path.suffix.lower()
        not in EDITABLE_EXTENSIONS
    ):
        raise ValueError(
            "This file cannot be edited as text"
        )

    path.write_text(
        contents,
        encoding="utf-8",
    )


def create_folder(
    server,
    parent: str,
    name: str,
):

    directory = safe_path(
        server,
        parent,
    )

    safe_name = Path(
        name
    ).name.strip()

    if not safe_name:
        raise ValueError(
            "Folder name required"
        )

    target = (
        directory / safe_name
    )

    target.mkdir(
        exist_ok=False
    )


def rename_entry(
    server,
    relative: str,
    new_name: str,
):

    path = safe_path(
        server,
        relative,
    )

    if not path.exists():
        raise FileNotFoundError(
            "File not found"
        )

    safe_name = Path(
        new_name
    ).name.strip()

    if not safe_name:
        raise ValueError(
            "Name required"
        )

    destination = (
        path.parent / safe_name
    )

    if destination.exists():
        raise FileExistsError(
            "Destination already exists"
        )

    path.rename(
        destination
    )


def delete_entry(
    server,
    relative: str,
):

    path = safe_path(
        server,
        relative,
    )

    root = server_root(server)

    if path == root:
        raise ValueError(
            "Cannot delete server root"
        )

    if path.is_dir():

        shutil.rmtree(
            path
        )

    elif path.is_file():

        path.unlink()

    else:

        raise FileNotFoundError(
            "File not found"
        )

def move_entry(
    server,
    source_relative: str,
    destination_relative: str,
):
    source = safe_path(
        server,
        source_relative,
    )

    destination_directory = safe_path(
        server,
        destination_relative,
    )

    if not source.exists():
        raise FileNotFoundError(
            "Source not found"
        )

    if not destination_directory.is_dir():
        raise ValueError(
            "Destination is not a directory"
        )

    target = (
        destination_directory
        / source.name
    )

    if target.exists():
        raise FileExistsError(
            "Destination already exists"
        )

    # Prevent moving a folder into itself
    # or one of its own descendants.
    if source.is_dir():

        try:
            destination_directory.relative_to(
                source
            )

            raise ValueError(
                "Cannot move a folder into itself"
            )

        except ValueError as error:

            if str(error) == (
                "Cannot move a folder into itself"
            ):
                raise

    source.rename(
        target
    )
