"""Local administrator recovery commands for installed consoles."""

import argparse
import os
import secrets

from .auth import hash_password
from .database import SessionLocal
from .models import AccessRole, User


def ensure_initial_admin(db, username: str, password: str | None = None):
    if db.query(User).filter(User.role == "admin").first():
        return None

    administrator = db.query(AccessRole).filter(AccessRole.name == "Administrator").first()

    temporary_password = password or secrets.token_urlsafe(18)
    db.add(
        User(
            username=username,
            password_hash=hash_password(temporary_password),
            role="admin",
            role_id=administrator.id if administrator else None,
            enabled=True,
            must_change_password=True,
        )
    )
    db.commit()
    return temporary_password


def reset_password(db, username: str, password: str | None = None):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise ValueError(f"User '{username}' was not found")

    temporary_password = password or secrets.token_urlsafe(18)
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    user.totp_secret = None
    user.totp_enabled = False
    user.enabled = True
    db.commit()
    return temporary_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage local STEMCraft Console users")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure = subparsers.add_parser("ensure-admin", help="Create the first administrator")
    ensure.add_argument("--username", default="admin")

    reset = subparsers.add_parser("reset-password", help="Reset a user's password")
    reset.add_argument("username", nargs="?", default="admin")

    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.command == "ensure-admin":
            password = ensure_initial_admin(
                db,
                args.username,
                os.getenv("STEMCRAFT_BOOTSTRAP_ADMIN_PASSWORD") or None,
            )
            if password:
                print(password)
            return 0

        password = reset_password(db, args.username)
        print(f"Password reset for {args.username}.")
        print(f"Temporary password: {password}")
        print("The user must change this password after signing in.")
        print("Two-factor authentication was disabled for account recovery.")
        return 0
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
