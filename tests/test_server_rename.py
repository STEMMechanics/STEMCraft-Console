import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Server, User
from app import web_properties


class JsonRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


def database_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_rename_server_changes_display_name_directory_and_service(monkeypatch, tmp_path):
    engine, db = database_session()
    try:
        user = User(username="admin", password_hash="unused", role="admin", enabled=True)
        server_directory = tmp_path / "survival"
        server_directory.mkdir()
        server = Server(
            name="Survival",
            directory=str(server_directory),
            service_name="survival-service",
        )
        db.add_all([user, server])
        db.commit()
        monkeypatch.setattr(
            web_properties,
            "get_accessible_server",
            lambda *_args: (user, server),
        )
        monkeypatch.setattr(web_properties, "register_server", lambda _server: None)

        confirmation = asyncio.run(
            web_properties.rename_server_api(
                server.id,
                JsonRequest({"name": "Creative"}),
                db,
            )
        )

        assert confirmation.status_code == 409
        confirmation_data = json.loads(confirmation.body)
        assert confirmation_data["rename_confirmation_required"] is True
        assert confirmation_data["directory"] == str(tmp_path / "creative")
        assert confirmation_data["service_name"] == "creative"

        result = asyncio.run(
            web_properties.rename_server_api(
                server.id,
                JsonRequest({"name": "Creative", "confirm": True}),
                db,
            )
        )

        assert result["server_name"] == "Creative"
        assert server.name == "Creative"
        assert server.directory == str(tmp_path / "creative")
        assert server.service_name == "creative"
        assert (tmp_path / "creative").is_dir()
        assert not server_directory.exists()
    finally:
        db.close()
        engine.dispose()


def test_rename_server_rejects_duplicate_name(monkeypatch, tmp_path):
    engine, db = database_session()
    try:
        user = User(username="admin", password_hash="unused", role="admin", enabled=True)
        server = Server(
            name="Survival",
            directory=str(tmp_path / "survival"),
            service_name="survival-service",
        )
        existing = Server(
            name="Creative",
            directory=str(tmp_path / "creative"),
            service_name="creative-service",
        )
        db.add_all([user, server, existing])
        db.commit()
        monkeypatch.setattr(
            web_properties,
            "get_accessible_server",
            lambda *_args: (user, server),
        )

        response = asyncio.run(
            web_properties.rename_server_api(
                server.id,
                JsonRequest({"name": "Creative"}),
                db,
            )
        )

        assert response.status_code == 409
        assert json.loads(response.body)["error"] == "Server name already exists"
        assert server.name == "Survival"
    finally:
        db.close()
        engine.dispose()


def test_rename_running_systemd_server_migrates_boot_policy_and_restarts(monkeypatch, tmp_path):
    engine, db = database_session()
    try:
        user = User(username="admin", password_hash="unused", role="admin", enabled=True)
        old_directory = tmp_path / "survival"
        old_directory.mkdir()
        server = Server(
            name="Survival",
            directory=str(old_directory),
            service_name="survival",
            process_backend="systemd",
        )
        db.add_all([user, server])
        db.commit()
        monkeypatch.setattr(
            web_properties,
            "get_accessible_server",
            lambda *_args: (user, server),
        )
        monkeypatch.setattr(web_properties, "register_server", lambda _server: None)
        monkeypatch.setattr(
            web_properties,
            "server_status",
            lambda _server_id: {"running": True, "enabled_at_boot": True},
        )
        stopped = []
        boot_changes = []
        starts = []
        monkeypatch.setattr(
            web_properties,
            "stop_server_and_wait",
            lambda server_id: stopped.append(server_id),
        )
        monkeypatch.setattr(
            web_properties,
            "set_systemd_enabled",
            lambda _server_id, enabled: boot_changes.append((server.service_name, enabled)),
        )
        monkeypatch.setattr(
            web_properties,
            "start_server",
            lambda _server_id, directory, *_args: starts.append(directory),
        )

        result = asyncio.run(
            web_properties.rename_server_api(
                server.id,
                JsonRequest({"name": "Creative World", "confirm": True}),
                db,
            )
        )

        assert stopped == [server.id]
        assert boot_changes == [("survival", False), ("creative-world", True)]
        assert starts == [str(tmp_path / "creative-world")]
        assert result["restarted"] is True
        assert server.service_name == "creative-world"
    finally:
        db.close()
        engine.dispose()
