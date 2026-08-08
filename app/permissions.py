from fastapi import HTTPException

from sqlalchemy.orm import Session

from .models import Server, User


def get_server_for_user(
    db: Session,
    server_id: int,
    user: User,
):

    server = db.get(
        Server,
        server_id,
    )

    if not server:

        raise HTTPException(
            status_code=404,
            detail="Server not found",
        )

    # Admin gets everything
    if user.role == "admin":
        return server

    # Normal user requires assignment
    for assigned_server in user.servers:

        if assigned_server.id == server.id:
            return server

    raise HTTPException(
        status_code=403,
        detail="You do not have access to this server",
    )