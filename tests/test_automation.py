from app import automation
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


def test_initial_metric_failure_does_not_prevent_automation_start(monkeypatch, caplog):
    started = []

    class FakeThread:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def is_alive(self):
            return False

        def start(self):
            started.append(True)

    monkeypatch.setattr(automation, "collect_metrics", lambda: (_ for _ in ()).throw(RuntimeError("metrics unavailable")))
    monkeypatch.setattr(automation.threading, "Thread", FakeThread)
    monkeypatch.setattr(automation, "_thread", None)

    automation.start_automation()

    assert started == [True]
    assert "Initial historical metric collection failed" in caplog.text
