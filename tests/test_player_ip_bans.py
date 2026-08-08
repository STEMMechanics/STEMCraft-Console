from types import SimpleNamespace

import pytest

from app import player_manager


def test_ban_ip_normalizes_address_and_sends_command(monkeypatch):
    commands = []
    monkeypatch.setattr(player_manager, "require_running", lambda server: None)
    monkeypatch.setattr(player_manager, "send_command", lambda server_id, command: commands.append(command))
    player_manager.ban_ip(SimpleNamespace(id=7), "2001:0db8::1")
    assert commands == ["ban-ip 2001:db8::1"]


def test_ban_ip_rejects_hostname(monkeypatch):
    monkeypatch.setattr(player_manager, "require_running", lambda server: None)
    with pytest.raises(RuntimeError, match="valid IPv4 or IPv6"):
        player_manager.ban_ip(SimpleNamespace(id=7), "example.com")
