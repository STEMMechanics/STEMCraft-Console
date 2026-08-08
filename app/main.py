import os

from dotenv import load_dotenv

load_dotenv(
    os.getenv(
        "STEMCRAFT_CONSOLE_ENV",
        ".env",
    )
)

from fastapi import FastAPI

from .version import APP_VERSION
from .auth import hash_password
from .config import COOKIE_SECURE, SECRET_KEY
from .migrations import upgrade_database
from .processes import register_server

from .database import (
    SessionLocal,
)

from .models import User

from .routers_auth import (
    router as auth_router,
)

from .routers_servers import (
    router as servers_router,
)

from .routers_users import (
    router as users_router,
)

from .routers_paper import (
    router as paper_router,
)

from .web_users import (
    router as web_users_router,
)

from .web_servers import (
    router as web_servers_router,
)

from .web_players import (
    router as web_players_router,
)

from .web_plugins import (
    router as web_plugins_router,
)

from .web_files import (
    router as web_files_router,
)

from .web_backups import (
    router as web_backups_router,
)

from .web_properties import (
    router as web_properties_router,
)

from .web_settings import (
    router as web_settings_router,
)
from .web_automation import router as web_automation_router
from .automation import start_automation, stop_automation

from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse

from .web import router as web_router

app = FastAPI(
    title="STEMCraft Server Console",
    version=APP_VERSION,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="strict",
    https_only=COOKIE_SECURE,
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
    )
    return response

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

app.include_router(web_router)

app.include_router(
    auth_router
)

app.include_router(
    users_router
)

app.include_router(
    servers_router
)

app.include_router(
    paper_router
)

app.include_router(
    web_users_router
)

app.include_router(
    web_servers_router
)

app.include_router(
    web_players_router
)

app.include_router(
    web_plugins_router
)

app.include_router(
    web_files_router
)

app.include_router(
    web_backups_router
)

app.include_router(
    web_properties_router
)

app.include_router(
    web_settings_router
)

app.include_router(web_automation_router)

@app.on_event("startup")
def startup():
    upgrade_database()
    create_initial_admin()
    db = SessionLocal()
    try:
        from .models import Server
        for server in db.query(Server).all():
            register_server(server)
    finally:
        db.close()
    start_automation()


@app.on_event("shutdown")
def shutdown():
    stop_automation()


def create_initial_admin():

    username = os.getenv(
        "STEMCRAFT_CONSOLE_ADMIN_USER"
    )

    password = os.getenv(
        "STEMCRAFT_CONSOLE_ADMIN_PASSWORD"
    )

    if not username or not password:
        return

    db = SessionLocal()

    try:

        existing_admin = (
            db.query(User)
            .filter(
                User.role == "admin"
            )
            .first()
        )

        if existing_admin:
            return

        user = User(
            username=username,

            password_hash=hash_password(
                password
            ),

            role="admin",

            enabled=True,
        )

        db.add(user)
        db.commit()

        print(
            f"Created admin user: "
            f"{username}"
        )

    finally:
        db.close()


@app.get("/")
def root():
    return RedirectResponse(
        "/dashboard",
        status_code=302,
    )

@app.get("/health")
def health():

    return {
        "status": "ok"
    }

@app.get("/api/version")
def version():
    return {
        "version": APP_VERSION,
    }
