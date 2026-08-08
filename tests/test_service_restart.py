import pytest

from app import service_restart


def test_restart_requires_systemd(monkeypatch):
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    with pytest.raises(RuntimeError, match="systemd service"):
        service_restart.schedule_console_restart()


def test_restart_schedules_controlled_exit(monkeypatch):
    monkeypatch.setenv("INVOCATION_ID", "test-invocation")
    created = {}

    class FakeThread:
        def __init__(self, *, target, args, daemon, name):
            created.update(target=target, args=args, daemon=daemon, name=name)

        def start(self):
            created["started"] = True

    monkeypatch.setattr(service_restart.threading, "Thread", FakeThread)

    service_restart.schedule_console_restart(delay=1.25)

    assert created == {
        "target": service_restart._exit_for_systemd_restart,
        "args": (1.25,),
        "daemon": True,
        "name": "console-systemd-restart",
        "started": True,
    }
