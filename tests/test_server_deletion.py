from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from app.database import Base
from app.models import Server, ServerMetric
from app import server_deletion


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def add_server(db, directory):
    server = Server(
        name="Survival",
        directory=str(directory),
        service_name="survival",
        process_backend="systemd",
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


def mock_stopped_server(monkeypatch):
    monkeypatch.setattr(server_deletion.processes, "register_server", lambda _server: None)
    monkeypatch.setattr(
        server_deletion.processes,
        "server_status",
        lambda _server_id: {"running": False},
    )


def test_delete_server_preserves_files_and_clears_history(db, tmp_path, monkeypatch):
    server_root = tmp_path / "servers"
    server_path = server_root / "survival"
    server_path.mkdir(parents=True)
    (server_path / "world.dat").write_text("world")
    server = add_server(db, server_path)
    db.add(ServerMetric(server_id=server.id, running=False))
    db.commit()
    unregistered = []
    mock_stopped_server(monkeypatch)
    monkeypatch.setattr(
        server_deletion.processes,
        "unregister_server",
        lambda server_id: unregistered.append(server_id),
    )

    result = server_deletion.delete_managed_server(
        db, server, delete_files=False, server_root=server_root,
    )

    assert result == {"deleted": True, "files_deleted": False, "warning": None}
    assert server_path.exists()
    assert db.query(Server).count() == 0
    assert db.query(ServerMetric).count() == 0
    assert unregistered == [server.id]


def test_delete_server_can_remove_managed_directory(db, tmp_path, monkeypatch):
    server_root = tmp_path / "servers"
    server_path = server_root / "creative"
    server_path.mkdir(parents=True)
    (server_path / "server.jar").write_text("jar")
    server = add_server(db, server_path)
    mock_stopped_server(monkeypatch)
    monkeypatch.setattr(server_deletion.processes, "unregister_server", lambda _id: None)

    result = server_deletion.delete_managed_server(
        db, server, delete_files=True, server_root=server_root,
    )

    assert result["files_deleted"] is True
    assert not server_path.exists()


def test_delete_server_stops_running_server_before_deleting(db, tmp_path, monkeypatch):
    server_root = tmp_path / "servers"
    server_path = server_root / "running"
    server_path.mkdir(parents=True)
    server = add_server(db, server_path)
    monkeypatch.setattr(server_deletion.processes, "register_server", lambda _server: None)
    statuses = iter(({"running": True}, {"running": False}))
    monkeypatch.setattr(
        server_deletion.processes, "server_status", lambda _server_id: next(statuses),
    )
    stopped = []
    monkeypatch.setattr(
        server_deletion.processes, "stop_server", lambda server_id: stopped.append(server_id),
    )
    monkeypatch.setattr(server_deletion.processes, "unregister_server", lambda _id: None)

    result = server_deletion.delete_managed_server(
        db, server, delete_files=False, server_root=server_root,
    )

    assert result["deleted"] is True
    assert stopped == [server.id]
    assert db.get(Server, server.id) is None


def test_delete_server_refuses_files_outside_managed_root(db, tmp_path, monkeypatch):
    server_root = tmp_path / "servers"
    server_root.mkdir()
    outside = tmp_path / "external-server"
    outside.mkdir()
    server = add_server(db, outside)
    mock_stopped_server(monkeypatch)

    with pytest.raises(ValueError, match="managed server directory"):
        server_deletion.delete_managed_server(
            db, server, delete_files=True, server_root=server_root,
        )

    assert outside.exists()
    assert db.get(Server, server.id) is not None
