from types import SimpleNamespace

import pytest

from app import player_manager


def test_online_players_supports_modern_paper_login_messages(monkeypatch):
    monkeypatch.setattr(player_manager, "server_status", lambda _server_id: {"running": True})
    monkeypatch.setattr(player_manager, "get_runtime_online_players", lambda _server_id: None)
    monkeypatch.setattr(player_manager, "get_console", lambda _server_id: [
        "[06:01:40 INFO]: nomadjimbob[/125.63.2.220:60595] logged in with entity id 299 at ([minecraft:overworld]-918.0, 89.0, 291.0)",
    ])

    assert player_manager.get_online_players(7) == {"nomadjimbob"}


def test_console_login_reconciles_empty_systemd_runtime_state(monkeypatch):
    monkeypatch.setattr(player_manager, "server_status", lambda _server_id: {"running": True})
    monkeypatch.setattr(player_manager, "get_runtime_online_players", lambda _server_id: set())
    monkeypatch.setattr(player_manager, "get_console", lambda _server_id: [
        "[06:09:15 INFO]: nomadjimbob[/125.63.25.220:60877] logged in with entity id 521 at ([minecraft:overworld]-918.0, 89.0, 291.0)",
    ])

    assert player_manager.get_online_players(7) == {"nomadjimbob"}


def test_console_disconnect_removes_stale_systemd_runtime_player(monkeypatch):
    monkeypatch.setattr(player_manager, "server_status", lambda _server_id: {"running": True})
    monkeypatch.setattr(player_manager, "get_runtime_online_players", lambda _server_id: {"nomadjimbob"})
    monkeypatch.setattr(player_manager, "get_console", lambda _server_id: [
        "[06:02:51 INFO]: nomadjimbob lost connection: Disconnected",
    ])

    assert player_manager.get_online_players(7) == set()


def test_online_players_supports_modern_paper_disconnect_messages(monkeypatch):
    monkeypatch.setattr(player_manager, "server_status", lambda _server_id: {"running": True})
    monkeypatch.setattr(player_manager, "get_runtime_online_players", lambda _server_id: None)
    monkeypatch.setattr(player_manager, "get_console", lambda _server_id: [
        "[06:01:40 INFO]: nomadjimbob[/125.63.2.220:60595] logged in with entity id 299 at ([minecraft:overworld]-918.0, 89.0, 291.0)",
        "[06:04:12 INFO]: nomadjimbob (/125.63.2.220:60595) lost connection: Disconnected",
    ])

    assert player_manager.get_online_players(7) == set()


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
