import io
import tarfile

import pytest

from app import update_manager
from app.update_manager import _safe_extract, install_release, normalize_version, rollback_release


def test_normalize_version_handles_release_prefix():
    assert normalize_version("v1.2.3") == (1, 2, 3)


def test_normalize_version_rejects_non_numeric_release():
    assert normalize_version("not-a-version") == (0,)


@pytest.mark.parametrize("tag", ["v1", "v../latest", "latest", "v1/2.0", "v1.2.3;id"])
def test_install_release_rejects_unsafe_tag_before_network(tag, tmp_path):
    with pytest.raises(ValueError, match="Invalid release tag"):
        install_release(tag, tmp_path)


def test_safe_extract_rejects_parent_path(tmp_path):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as archive:
        member = tarfile.TarInfo("../outside")
        member.size = 1
        archive.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="unsafe path"):
        _safe_extract(data.getvalue(), tmp_path)


def test_rollback_release_restores_snapshot(monkeypatch, tmp_path):
    for name in ("app", "migrations"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "value.txt").write_text("new")
    for name in ("alembic.ini", "requirements.txt"):
        (tmp_path / name).write_text("new")
    backup = tmp_path / ".updates" / "20260808T120000Z"
    backup.mkdir(parents=True)
    for name in ("app", "migrations"):
        (backup / name).mkdir()
        (backup / name / "value.txt").write_text("old")
    for name in ("alembic.ini", "requirements.txt"):
        (backup / name).write_text("old")
    monkeypatch.setattr(update_manager.subprocess, "run", lambda *args, **kwargs: None)

    result = rollback_release("20260808T120000Z", tmp_path)

    assert result["restart_required"] is True
    assert (tmp_path / "app" / "value.txt").read_text() == "old"
    assert (tmp_path / "requirements.txt").read_text() == "old"


def test_rollback_release_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="Invalid rollback identifier"):
        rollback_release("../20260808T120000Z", tmp_path)
