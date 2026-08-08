import os

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)

from sqlalchemy.orm import Session

from .auth import hash_password
from .database import get_db
from .models import Server, User
from .web_context import build_web_context
from .web_render import render_page
from .web_users import current_web_user

from .emailer import send_email
from .settings_manager import (
    get_smtp_settings,
    save_smtp_settings,
)

from .tfa import (
    generate_recovery_codes,
    generate_totp_secret,
    provisioning_uri,
    qr_code_data_uri,
    verify_totp,
)

from .auth import (
    hash_password,
    verify_password,
)

from .models import (
    RecoveryCode,
    Server,
    User,
)

from .update_manager import (
    get_latest_release,
    install_release,
    rollback_release,
)

router = APIRouter()


@router.get(
    "/settings",
    response_class=HTMLResponse,
)
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return RedirectResponse(
            "/login"
        )

    context = build_web_context(
        db,
        user,
    )

    database_path = Path(
        os.getenv(
            "STEMCRAFT_CONSOLE_DATABASE",
            "stemcraft-console.db",
        )
    ).expanduser()


    server_root = Path(
        os.getenv(
            "STEMCRAFT_CONSOLE_SERVER_ROOT",
            "minecraft-servers",
        )
    ).expanduser()


    console_host = os.getenv(
        "STEMCRAFT_CONSOLE_HOST",
        "127.0.0.1",
    )


    console_port = os.getenv(
        "STEMCRAFT_CONSOLE_PORT",
        "8000",
    )

    context.update({
        "page_title": "Settings",
        "active_page": "settings",

        "database_path":
            str(database_path),

        "server_root":
            str(server_root),

        "console_host":
            console_host,

        "console_port":
            console_port,
    })

    if user.role == "admin":

        context["users"] = (
            db.query(User)
            .order_by(User.username)
            .all()
        )

        context["servers"] = (
            db.query(Server)
            .order_by(Server.name)
            .all()
        )

    return render_page(
        request,
        "settings.html",
        "partials/settings.html",
        context,
    )


@router.post(
    "/api/web/settings/profile"
)
async def update_profile(
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    data = await request.json()

    username = (
        data.get(
            "username",
            ""
        )
        .strip()
    )

    email = (
        data.get(
            "email",
            ""
        )
        .strip()
    )

    password = (
        data.get(
            "password",
            ""
        )
    )

    if len(username) < 3:
        return JSONResponse(
            {
                "error":
                    "Username must be at least 3 characters."
            },
            status_code=400,
        )

    existing = (
        db.query(User)
        .filter(
            User.username == username,
            User.id != user.id,
        )
        .first()
    )

    if existing:
        return JSONResponse(
            {
                "error":
                    "Username already exists."
            },
            status_code=409,
        )

    user.username = username

    if email:

        existing_email = (
            db.query(User)
            .filter(
                User.email == email,
                User.id != user.id,
            )
            .first()
        )

        if existing_email:

            return JSONResponse(
                {
                    "error":
                        "Email address is already in use."
                },
                status_code=409,
            )

        user.email = email

    else:

        user.email = None

    if password:

        if len(password) < 8:
            return JSONResponse(
                {
                    "error":
                        "Password must be at least 8 characters."
                },
                status_code=400,
            )

        user.password_hash = hash_password(
            password
        )

    db.commit()

    return {
        "success": True
    }


@router.get(
    "/api/web/settings/users/{user_id}"
)
def get_user_settings(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = current_web_user(
        request,
        db,
    )

    if not admin:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if admin.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    user = db.get(
        User,
        user_id,
    )

    if not user:
        return JSONResponse(
            {"error": "User not found"},
            status_code=404,
        )

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "enabled": user.enabled,
        "must_change_password":
            user.must_change_password,

        "servers": [
            server.id
            for server in user.servers
        ],
    }


@router.post(
    "/api/web/settings/users"
)
async def create_user_settings(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = current_web_user(
        request,
        db,
    )

    if not admin:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if admin.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    data = await request.json()

    username = (
        data.get(
            "username",
            ""
        )
        .strip()
    )

    password = (
        data.get(
            "password",
            ""
        )
    )

    role = data.get(
        "role",
        "user",
    )

    must_change_password = bool(
        data.get(
            "must_change_password",
            True,
        )
    )

    if len(username) < 3:
        return JSONResponse(
            {"error": "Invalid username"},
            status_code=400,
        )

    if len(password) < 8:
        return JSONResponse(
            {
                "error":
                    "Password must be at least 8 characters."
            },
            status_code=400,
        )

    if role not in (
        "admin",
        "user",
    ):
        return JSONResponse(
            {"error": "Invalid role"},
            status_code=400,
        )

    existing = (
        db.query(User)
        .filter(
            User.username == username
        )
        .first()
    )

    if existing:
        return JSONResponse(
            {
                "error":
                    "Username already exists."
            },
            status_code=409,
        )

    user = User(
        username=username,
        password_hash=hash_password(
            password
        ),
        role=role,
        enabled=True,
        must_change_password=must_change_password,
    )

    db.add(user)
    db.flush()

    if role == "user":

        server_ids = data.get(
            "servers",
            [],
        )

        for server_id in server_ids:

            server = db.get(
                Server,
                int(server_id),
            )

            if server:
                user.servers.append(
                    server
                )

    db.commit()

    return {
        "success": True,
        "user_id": user.id,
    }


@router.post(
    "/api/web/settings/users/{user_id}"
)
async def update_user_settings(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = current_web_user(
        request,
        db,
    )

    if not admin:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if admin.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    user = db.get(
        User,
        user_id,
    )

    if not user:
        return JSONResponse(
            {"error": "User not found"},
            status_code=404,
        )

    data = await request.json()

    username = (
        data.get(
            "username",
            user.username,
        )
        .strip()
    )

    role = data.get(
        "role",
        user.role,
    )

    enabled = bool(
        data.get(
            "enabled",
            True,
        )
    )

    must_change_password = bool(
        data.get(
            "must_change_password",
            user.must_change_password,
        )
    )

    if role not in (
        "admin",
        "user",
    ):
        return JSONResponse(
            {"error": "Invalid role"},
            status_code=400,
        )

    if (
        user.id == admin.id
        and role != "admin"
    ):
        return JSONResponse(
            {
                "error":
                    "You cannot remove your own admin access."
            },
            status_code=400,
        )

    existing = (
        db.query(User)
        .filter(
            User.username == username,
            User.id != user.id,
        )
        .first()
    )

    if existing:
        return JSONResponse(
            {
                "error":
                    "Username already exists."
            },
            status_code=409,
        )

    user.username = username
    user.role = role
    user.enabled = enabled
    user.must_change_password = (
        must_change_password
    )

    password = data.get(
        "password",
        "",
    )

    if password:

        if len(password) < 8:
            return JSONResponse(
                {
                    "error":
                        "Password must be at least 8 characters."
                },
                status_code=400,
            )

        user.password_hash = hash_password(
            password
        )

    if role == "admin":

        user.servers.clear()

    else:

        server_ids = {
            int(server_id)
            for server_id
            in data.get(
                "servers",
                [],
            )
        }

        user.servers.clear()

        for server_id in server_ids:

            server = db.get(
                Server,
                server_id,
            )

            if server:
                user.servers.append(
                    server
                )

    db.commit()

    return {
        "success": True
    }


@router.delete(
    "/api/web/settings/users/{user_id}"
)
def delete_user_settings(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = current_web_user(
        request,
        db,
    )

    if not admin:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if admin.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    user = db.get(
        User,
        user_id,
    )

    if not user:
        return JSONResponse(
            {"error": "User not found"},
            status_code=404,
        )

    if user.id == admin.id:
        return JSONResponse(
            {
                "error":
                    "You cannot delete yourself."
            },
            status_code=400,
        )

    db.delete(user)
    db.commit()

    return {
        "success": True
    }

@router.get(
    "/api/web/settings/smtp"
)
def get_smtp_settings_api(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = current_web_user(
        request,
        db,
    )

    if not admin:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if admin.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    settings = get_smtp_settings(
        db
    )

    # Don't send the saved password back
    # to the browser.
    settings["smtp_password"] = ""

    return settings


@router.post(
    "/api/web/settings/smtp"
)
async def save_smtp_settings_api(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = current_web_user(
        request,
        db,
    )

    if not admin:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if admin.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    data = await request.json()

    existing = get_smtp_settings(
        db
    )

    # Blank password means keep the current one.
    if not data.get("smtp_password"):
        data["smtp_password"] = (
            existing["smtp_password"]
        )

    security = data.get(
        "smtp_security",
        "starttls",
    )

    if security not in (
        "starttls",
        "ssl",
        "none",
    ):
        return JSONResponse(
            {"error": "Invalid SMTP security mode"},
            status_code=400,
        )

    try:
        port = int(
            data.get(
                "smtp_port",
                587,
            )
        )

        if not (
            1 <= port <= 65535
        ):
            raise ValueError()

    except ValueError:

        return JSONResponse(
            {"error": "Invalid SMTP port"},
            status_code=400,
        )

    data["smtp_port"] = str(
        port
    )

    save_smtp_settings(
        db,
        data,
    )

    return {
        "success": True
    }


@router.post(
    "/api/web/settings/smtp/test"
)
async def test_smtp_settings(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = current_web_user(
        request,
        db,
    )

    if not admin:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if admin.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    if not admin.email:

        return JSONResponse(
            {
                "error":
                    "Add an email address to your profile first."
            },
            status_code=400,
        )

    try:

        send_email(
            db,
            admin.email,
            "STEMCraft Console SMTP Test",
            (
                "Your STEMCraft Console SMTP settings "
                "are working correctly."
            ),
        )

    except Exception as error:

        return JSONResponse(
            {"error": str(error)},
            status_code=400,
        )

    return {
        "success": True
    }

@router.get(
    "/api/web/settings/tfa"
)
def tfa_status(
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    return {
        "enabled":
            user.totp_enabled,
    }

@router.post(
    "/api/web/settings/tfa/setup"
)
def tfa_setup(
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if user.totp_enabled:

        return JSONResponse(
            {"error": "2FA is already enabled"},
            status_code=400,
        )


    secret = generate_totp_secret()

    user.totp_secret = secret

    db.commit()


    uri = provisioning_uri(
        user,
        secret,
    )


    return {
        "secret": secret,

        "qr_code":
            qr_code_data_uri(
                uri
            ),
    }

@router.post(
    "/api/web/settings/tfa/confirm"
)
async def tfa_confirm(
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )


    data = await request.json()

    code = (
        data.get(
            "code",
            ""
        )
    )


    if not user.totp_secret:

        return JSONResponse(
            {"error": "2FA setup has not been started"},
            status_code=400,
        )


    if not verify_totp(
        user.totp_secret,
        code,
    ):

        return JSONResponse(
            {"error": "Invalid authentication code"},
            status_code=400,
        )


    user.totp_enabled = True

    db.commit()


    recovery_codes = (
        generate_recovery_codes(
            db,
            user,
        )
    )


    return {
        "success": True,

        "recovery_codes":
            recovery_codes,
    }

@router.post(
    "/api/web/settings/tfa/disable"
)
async def tfa_disable(
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )


    data = await request.json()

    password = (
        data.get(
            "password",
            ""
        )
    )


    if not verify_password(
        password,
        user.password_hash,
    ):

        return JSONResponse(
            {"error": "Incorrect password"},
            status_code=400,
        )


    user.totp_enabled = False
    user.totp_secret = None

    db.query(
        RecoveryCode
    ).filter(
        RecoveryCode.user_id
        == user.id
    ).delete()

    db.commit()


    return {
        "success": True
    }

@router.post(
    "/api/web/settings/tfa/recovery-codes"
)
async def regenerate_recovery_codes(
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if not user.totp_enabled:

        return JSONResponse(
            {"error": "2FA is not enabled"},
            status_code=400,
        )


    codes = generate_recovery_codes(
        db,
        user,
    )


    return {
        "recovery_codes":
            codes,
    }

@router.get(
    "/api/web/settings/update"
)
def update_status(
    request: Request,
    db: Session = Depends(get_db),
):

    user = current_web_user(
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if user.role != "admin":
        return JSONResponse(
            {"error": "Admin required"},
            status_code=403,
        )

    try:

        return get_latest_release()

    except Exception as error:

        return JSONResponse(
            {
                "error":
                    "Unable to check GitHub releases",

                "detail":
                    str(error),
            },
            status_code=502,
        )


@router.post("/api/web/settings/update")
async def install_update(request: Request, db: Session = Depends(get_db)):
    user = current_web_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if user.role != "admin":
        return JSONResponse({"error": "Admin required"}, status_code=403)
    data = await request.json()
    try:
        if data.get("action") == "rollback":
            return rollback_release(str(data.get("rollback_id", "")))
        return install_release(str(data.get("tag", "")))
    except Exception as error:
        return JSONResponse({"error": str(error)}, status_code=400)
