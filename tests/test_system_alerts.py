from datetime import datetime
from types import SimpleNamespace

from app import system_alerts


class Query:
    def filter(self, *_args):
        return self

    def all(self):
        return [SimpleNamespace(
            email="admin@example.com", enabled=True,
            can=lambda permission: permission == "settings.manage",
        )]


class DB:
    def query(self, *_args):
        return Query()

    def commit(self):
        pass


def test_threshold_alert_has_persisted_cooldown(monkeypatch):
    values = {}
    sent = []
    monkeypatch.setattr(system_alerts, "get_system_alert_settings", lambda _db: {
        "enabled": True, "memory_percent": 95, "storage_percent": 80,
        "cooldown_minutes": 60,
    })
    monkeypatch.setattr(system_alerts.psutil, "virtual_memory", lambda: SimpleNamespace(percent=96))
    monkeypatch.setattr(system_alerts.shutil, "disk_usage", lambda _path: SimpleNamespace(used=81, total=100))
    monkeypatch.setattr(system_alerts, "get_setting", lambda _db, key: values.get(key, ""))
    monkeypatch.setattr(system_alerts, "set_setting", lambda _db, key, value: values.__setitem__(key, value))
    monkeypatch.setattr(system_alerts, "send_email", lambda _db, address, subject, body: sent.append((address, subject, body)))
    now = datetime(2026, 8, 18, 12, 0)

    assert system_alerts.check_system_alerts(DB(), now) == ["memory", "storage"]
    assert system_alerts.check_system_alerts(DB(), now) == []
    assert len(sent) == 2
