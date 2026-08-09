import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import offsite_backups
from app.offsite_backups import OffsiteBackupError


def completed(stdout=""):
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def test_lists_configured_rclone_remotes(monkeypatch):
    monkeypatch.setattr(offsite_backups.shutil, "which", lambda name: "/usr/bin/rclone")
    monkeypatch.setattr(offsite_backups.subprocess, "run", lambda *args, **kwargs: completed("storj:\nb2:\n"))

    assert offsite_backups.configured_remotes(refresh=True) == ["b2", "storj"]


def test_destination_must_use_a_configured_remote(monkeypatch):
    monkeypatch.setattr(offsite_backups, "configured_remotes", lambda: ["b2"])

    assert offsite_backups.validate_destination("b2:bucket/backups/") == "b2:bucket/backups"
    with pytest.raises(OffsiteBackupError, match="not configured"):
        offsite_backups.validate_destination("sftp:backups")


def test_upload_uses_copyto_without_a_shell(monkeypatch, tmp_path):
    server_root = tmp_path / "creative"
    backup_dir = server_root / "backups"
    backup_dir.mkdir(parents=True)
    (backup_dir / "save.zip").write_bytes(b"backup")
    server = SimpleNamespace(directory=str(server_root))
    commands = []
    monkeypatch.setattr(offsite_backups, "configured_remotes", lambda: ["b2"])
    monkeypatch.setattr(offsite_backups, "_run_rclone", lambda *args: commands.append(args) or completed())

    remote = offsite_backups.upload_backup(server, "save.zip", "b2:bucket/panel")

    assert remote == "b2:bucket/panel/creative/save.zip"
    assert commands == [("copyto", str(backup_dir / "save.zip"), remote, "--transfers", "1", "--checkers", "1")]


def test_remote_retention_deletes_only_old_zip_files(monkeypatch, tmp_path):
    server = SimpleNamespace(directory=str(tmp_path / "survival"))
    deleted = []
    listing = json.dumps([
        {"Name": "new.zip", "ModTime": "2026-08-09T02:00:00Z"},
        {"Name": "notes.txt", "ModTime": "2026-08-09T01:30:00Z"},
        {"Name": "old.zip", "ModTime": "2026-08-09T01:00:00Z"},
    ])
    monkeypatch.setattr(offsite_backups, "configured_remotes", lambda: ["sftp"])

    def run(*args):
        if args[0] == "lsjson":
            return completed(listing)
        deleted.append(args)
        return completed()

    monkeypatch.setattr(offsite_backups, "_run_rclone", run)

    assert offsite_backups.enforce_remote_retention(server, "sftp:backups", 1) == ["old.zip"]
    assert deleted == [("deletefile", "sftp:backups/survival/old.zip")]


def test_missing_rclone_has_actionable_error(monkeypatch):
    monkeypatch.setattr(offsite_backups.shutil, "which", lambda name: None)

    with pytest.raises(OffsiteBackupError, match="not installed"):
        offsite_backups.configured_remotes(refresh=True)
