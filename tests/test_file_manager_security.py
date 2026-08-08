from types import SimpleNamespace

import pytest

from app.file_manager import delete_entry, format_size, safe_path


def test_safe_path_rejects_parent_traversal(tmp_path):
    server = SimpleNamespace(directory=str(tmp_path / "server"))
    (tmp_path / "server").mkdir()

    with pytest.raises(ValueError, match="Invalid path"):
        safe_path(server, "../outside.txt")


def test_safe_path_rejects_symlink_escape(tmp_path):
    root = tmp_path / "server"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    server = SimpleNamespace(directory=str(root))

    with pytest.raises(ValueError, match="Invalid path"):
        safe_path(server, "escape/secret.txt")


def test_delete_entry_refuses_server_root(tmp_path):
    server = SimpleNamespace(directory=str(tmp_path))

    with pytest.raises(ValueError, match="Cannot delete server root"):
        delete_entry(server, "")


def test_format_size_spells_out_bytes():
    assert format_size(491) == "491 Bytes"
