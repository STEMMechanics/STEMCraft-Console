import sqlite3
from pathlib import Path

from app import migrations


def test_upgrade_database_targets_head(monkeypatch):
    called = {}

    def fake_upgrade(config, revision):
        called["script_location"] = config.get_main_option("script_location")
        called["revision"] = revision

    monkeypatch.setattr(migrations.command, "upgrade", fake_upgrade)

    migrations.upgrade_database()

    assert called["revision"] == "head"
    assert called["script_location"].endswith("/migrations")


def test_migration_scripts_are_packaged():
    versions = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    scripts = list(versions.glob("*.py"))

    assert scripts, "Release is missing migrations/versions/*.py"


def test_clean_database_migrates_to_application_schema(monkeypatch, tmp_path):
    database = tmp_path / "console.db"
    monkeypatch.setenv("STEMCRAFT_CONSOLE_DATABASE", str(database))

    migrations.upgrade_database()

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"users", "servers", "alembic_version"} <= tables
