import hashlib
import io
import pytest
import json
import zipfile

from app import paper


def _build(payload: bytes, checksum: str):
    return {
        "id": 42,
        "downloads": {
            "server:default": {
                "url": "https://example.invalid/paper.jar",
                "checksums": {"sha256": checksum},
            }
        },
    }


def test_download_paper_verifies_and_atomically_replaces(monkeypatch, tmp_path):
    payload = b"new jar"
    (tmp_path / "paper.jar").write_bytes(b"old jar")
    monkeypatch.setattr(
        paper, "get_latest_build",
        lambda version: _build(payload, hashlib.sha256(payload).hexdigest()),
    )
    monkeypatch.setattr(
        paper.urllib.request, "urlopen",
        lambda *args, **kwargs: io.BytesIO(payload),
    )

    result = paper.download_paper("1.21.4", str(tmp_path))

    assert result["build"] == "42"
    assert (tmp_path / "paper.jar").read_bytes() == payload
    assert not (tmp_path / ".paper.jar.download").exists()


def test_download_paper_keeps_existing_jar_on_bad_checksum(monkeypatch, tmp_path):
    payload = b"corrupt"
    (tmp_path / "paper.jar").write_bytes(b"known good")
    monkeypatch.setattr(
        paper, "get_latest_build", lambda version: _build(payload, "0" * 64)
    )
    monkeypatch.setattr(
        paper.urllib.request, "urlopen",
        lambda *args, **kwargs: io.BytesIO(payload),
    )

    with pytest.raises(ValueError, match="SHA-256"):
        paper.download_paper("1.21.4", str(tmp_path))

    assert (tmp_path / "paper.jar").read_bytes() == b"known good"
    assert not (tmp_path / ".paper.jar.download").exists()


def test_download_paper_rejects_invalid_version(tmp_path):
    with pytest.raises(ValueError, match="Invalid Paper version"):
        paper.download_paper("../../escape", str(tmp_path))


def test_download_paper_uses_configured_jar_name(monkeypatch, tmp_path):
    payload = b"paper"
    monkeypatch.setattr(paper, "get_latest_build", lambda version: _build(payload, hashlib.sha256(payload).hexdigest()))
    monkeypatch.setattr(paper.urllib.request, "urlopen", lambda request, timeout=0: io.BytesIO(payload))

    result = paper.download_paper("1.21.4", str(tmp_path), "server.jar")

    assert (tmp_path / "server.jar").read_bytes() == payload
    assert result["path"].endswith("server.jar")


def test_get_versions_sorts_grouped_versions_numerically(monkeypatch):
    response = io.BytesIO(b'{"versions":{"legacy":["1.7.10"],"current":["1.21.10","1.21.9"]}}')
    monkeypatch.setattr(paper.urllib.request, "urlopen", lambda *args, **kwargs: response)

    assert paper.get_versions() == ["1.21.10", "1.21.9", "1.7.10"]


def test_download_paper_installs_explicit_build(monkeypatch, tmp_path):
    old_payload = b"old"
    selected_payload = b"selected"
    builds = [
        _build(old_payload, hashlib.sha256(old_payload).hexdigest()) | {"id": 111},
        _build(selected_payload, hashlib.sha256(selected_payload).hexdigest()) | {"id": 107},
    ]
    monkeypatch.setattr(paper, "get_builds", lambda version: builds)
    monkeypatch.setattr(paper.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(selected_payload))

    result = paper.download_paper("26.2", str(tmp_path), build_id=107)

    assert result["build"] == "107"
    assert (tmp_path / "paper.jar").read_bytes() == selected_payload


def test_inspect_paper_jar_reads_version_and_matches_published_build(tmp_path):
    jar = tmp_path / "paper.jar"
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr("version.json", json.dumps({"id": "26.2"}))
    checksum = hashlib.sha256(jar.read_bytes()).hexdigest()
    builds = [
        {"id": 111, "downloads": {"server:default": {"checksums": {"sha256": "0" * 64}}}},
        {"id": 63, "downloads": {"server:default": {"checksums": {"sha256": checksum}}}},
    ]

    inspection = paper.inspect_paper_jar(jar)

    assert inspection == {"version": "26.2", "sha256": checksum}
    assert paper.match_paper_build(inspection["sha256"], builds) == "63"


def test_inspect_paper_jar_rejects_non_paper_jar(tmp_path):
    jar = tmp_path / "server.jar"
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")

    with pytest.raises(ValueError, match="identify the installed Paper JAR"):
        paper.inspect_paper_jar(jar)
