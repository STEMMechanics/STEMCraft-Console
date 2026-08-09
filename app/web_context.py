from sqlalchemy.orm import Session

from .models import Server, User

from .version import APP_VERSION
from .permissions import has_permission

def get_available_servers(
    db: Session,
    user: User,
):
    if not has_permission(user, "servers.view"):
        return []

    if has_permission(user, "servers.view_all"):
        return (
            db.query(Server)
            .order_by(Server.name)
            .all()
        )

    return sorted(
        user.servers,
        key=lambda server: server.name.lower(),
    )


def build_web_context(
    db: Session,
    user: User,
    active_server=None,
):
    available_servers = get_available_servers(
        db,
        user,
    )

    if (
        active_server is None
        and available_servers
    ):
        active_server = available_servers[0]

    return {
        "user": user,
        "available_servers": available_servers,
        "active_server": active_server,
        "app_version": APP_VERSION,
    }
