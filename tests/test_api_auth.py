from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import User
from app.routers_auth import login


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _form():
    return SimpleNamespace(username="alice", password="correct horse battery staple")


@pytest.mark.parametrize(
    "attributes, expected",
    [
        ({"totp_enabled": True}, "two-factor"),
        ({"must_change_password": True}, "Change your password"),
    ],
)
def test_api_login_cannot_bypass_account_security_state(db, attributes, expected):
    user = User(
        username="alice",
        password_hash=hash_password(_form().password),
        role="admin",
        enabled=True,
        **attributes,
    )
    db.add(user)
    db.commit()

    with pytest.raises(HTTPException) as caught:
        login(_form(), db)

    assert caught.value.status_code == 403
    assert expected in caught.value.detail
