from types import SimpleNamespace

import pytest

from app import admin_cli


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, result=None):
        self.result = result
        self.added = None
        self.committed = False

    def query(self, _model):
        return FakeQuery(self.result)

    def add(self, user):
        self.added = user

    def commit(self):
        self.committed = True


def test_initial_admin_is_hashed_and_requires_password_change(monkeypatch):
    db = FakeSession()
    monkeypatch.setattr(admin_cli.secrets, "token_urlsafe", lambda _length: "temporary-secret")
    monkeypatch.setattr(admin_cli, "hash_password", lambda value: f"hashed:{value}")

    password = admin_cli.ensure_initial_admin(db, "admin")

    assert password == "temporary-secret"
    assert db.added.password_hash == "hashed:temporary-secret"
    assert db.added.must_change_password is True
    assert db.committed is True


def test_initial_admin_does_not_replace_existing_admin():
    db = FakeSession(SimpleNamespace(role="admin"))

    assert admin_cli.ensure_initial_admin(db, "admin") is None
    assert db.added is None


def test_reset_password_recovers_account_and_disables_totp(monkeypatch):
    user = SimpleNamespace(
        username="admin", password_hash="old", must_change_password=False,
        totp_secret="secret", totp_enabled=True, enabled=False,
    )
    db = FakeSession(user)
    monkeypatch.setattr(admin_cli, "hash_password", lambda value: f"hashed:{value}")

    password = admin_cli.reset_password(db, "admin", "new-password")

    assert password == "new-password"
    assert user.password_hash == "hashed:new-password"
    assert user.must_change_password is True
    assert user.totp_secret is None
    assert user.totp_enabled is False
    assert user.enabled is True


def test_reset_password_rejects_unknown_user():
    with pytest.raises(ValueError, match="was not found"):
        admin_cli.reset_password(FakeSession(), "missing")
