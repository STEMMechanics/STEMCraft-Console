"""Safe rclone integration for optional off-site backup copies."""

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


class OffsiteBackupError(RuntimeError):
    pass


_remote_cache: tuple[float, list[str]] = (0, [])
_DESTINATION = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")


def _rclone_command(*args: str) -> list[str]:
    executable = shutil.which("rclone")
    if not executable:
        raise OffsiteBackupError("rclone is not installed on the console server")
    command = [executable, *args]
    config = os.getenv("STEMCRAFT_RCLONE_CONFIG", "").strip()
    if config:
        command.extend(["--config", str(Path(config).expanduser())])
    return command


def _run_rclone(*args: str) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            _rclone_command(*args), capture_output=True, text=True, check=False,
            timeout=max(30, int(os.getenv("STEMCRAFT_RCLONE_TIMEOUT_SECONDS", "3600"))),
        )
    except subprocess.TimeoutExpired as error:
        raise OffsiteBackupError("Off-site transfer timed out") from error
    if result.returncode:
        detail = (result.stderr or result.stdout or "rclone failed").strip().splitlines()[-1]
        raise OffsiteBackupError(detail[:500])
    return result


def configured_remotes(refresh=False) -> list[str]:
    global _remote_cache
    now = time.monotonic()
    if not refresh and now - _remote_cache[0] < 60:
        return list(_remote_cache[1])
    remotes = sorted(line.strip().removesuffix(":") for line in _run_rclone("listremotes").stdout.splitlines() if line.strip())
    _remote_cache = (now, remotes)
    return list(remotes)


def validate_destination(destination: str, check_configured=True) -> str:
    destination = destination.strip().rstrip("/")
    match = _DESTINATION.fullmatch(destination)
    if not match or not match.group(2) or any(character in destination for character in "\r\n\0"):
        raise OffsiteBackupError("Use an rclone destination such as b2:bucket/backups")
    if check_configured and match.group(1) not in configured_remotes():
        raise OffsiteBackupError(f"rclone remote {match.group(1)!r} is not configured")
    return destination


def remote_backup_directory(destination: str, server) -> str:
    server_folder = Path(server.directory).resolve().name
    return f"{validate_destination(destination)}/{server_folder}"


def upload_backup(server, filename: str, destination: str) -> str:
    from .backup_manager import safe_backup_path

    local_path = safe_backup_path(server, filename)
    remote_directory = remote_backup_directory(destination, server)
    remote_file = f"{remote_directory}/{local_path.name}"
    _run_rclone("copyto", str(local_path), remote_file, "--transfers", "1", "--checkers", "1")
    return remote_file


def test_destination(destination: str) -> None:
    _run_rclone("lsd", validate_destination(destination), "--max-depth", "1")


def enforce_remote_retention(server, destination: str, keep: int | None) -> list[str]:
    if not keep or keep < 1:
        return []
    remote_directory = remote_backup_directory(destination, server)
    result = _run_rclone("lsjson", remote_directory, "--files-only")
    try:
        files = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as error:
        raise OffsiteBackupError("rclone returned an invalid file list") from error
    backups = sorted(
        (item for item in files if str(item.get("Name", "")).lower().endswith(".zip")),
        key=lambda item: str(item.get("ModTime", "")), reverse=True,
    )
    deleted = []
    for item in backups[keep:]:
        name = Path(str(item["Name"])).name
        _run_rclone("deletefile", f"{remote_directory}/{name}")
        deleted.append(name)
    return deleted
