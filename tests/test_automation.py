from app.automation import enforce_backup_retention


def test_backup_retention_deletes_only_backups_beyond_limit(monkeypatch):
    backups = [{"filename": name} for name in ("new.zip", "middle.zip", "old.zip")]
    deleted = []
    monkeypatch.setattr("app.automation.list_backups", lambda server: backups)
    monkeypatch.setattr("app.automation.delete_backup", lambda server, name: deleted.append(name))

    enforce_backup_retention(object(), 2)

    assert deleted == ["old.zip"]


def test_backup_retention_can_be_unlimited(monkeypatch):
    monkeypatch.setattr("app.automation.list_backups", lambda server: (_ for _ in ()).throw(AssertionError()))
    enforce_backup_retention(object(), None)
