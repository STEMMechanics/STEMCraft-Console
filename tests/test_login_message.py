from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.settings_manager import (
    DEFAULT_LOGIN_MESSAGE,
    get_login_message,
    save_login_message,
)


def test_login_message_defaults_and_can_be_customized():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        assert get_login_message(db) == DEFAULT_LOGIN_MESSAGE
        assert save_login_message(db, "  Welcome, builders!  ") == "Welcome, builders!"
        assert get_login_message(db) == "Welcome, builders!"
        assert save_login_message(db, "  ") == DEFAULT_LOGIN_MESSAGE
    finally:
        db.close()
        engine.dispose()


def test_login_page_renders_saved_message():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    save_login_message(db, "Welcome to our family server!")
    db.close()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/login")
        assert response.status_code == 200
        assert "Welcome to our family server!" in response.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
