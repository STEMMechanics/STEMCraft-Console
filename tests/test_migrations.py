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
