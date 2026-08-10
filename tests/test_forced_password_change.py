from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password, verify_password
from app.database import Base, get_db
from app.main import app
from app.models import User
import app.main as main_module


def test_temporary_password_requires_change_before_web_access(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = session_factory()
    user = User(
        username="admin",
        password_hash=hash_password("temporary-password"),
        role="admin",
        enabled=True,
        must_change_password=True,
    )
    db.add(user)
    db.commit()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(main_module, "SessionLocal", session_factory)
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        response = client.post(
            "/login",
            data={"username": "admin", "password": "temporary-password"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/change-password"

        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/change-password"

        response = client.get("/api/system/stats")
        assert response.status_code == 403

        response = client.post(
            "/change-password",
            data={"password": "new-secure-password", "confirm_password": "new-secure-password"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

        db.expire_all()
        updated = db.get(User, user.id)
        assert updated.must_change_password is False
        assert verify_password("new-secure-password", updated.password_hash)
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        engine.dispose()
