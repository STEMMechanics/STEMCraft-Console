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

from .database import get_db

from .player_manager import (
    ban_player,
    deop_player,
    get_player_data,
    kick_player,
    op_player,
    pardon_player,
    remove_whitelist,
    set_whitelist_enabled,
    whitelist_player,
    ban_ip,
    pardon_ip,
)

from .web_context import (
    build_web_context,
)

from .web_render import (
    render_page,
)

from .web_servers import (
    current_web_user,
    get_accessible_server,
)
from .permissions import has_permission


router = APIRouter()


@router.get(
    "/servers/{server_id}/players",
    response_class=HTMLResponse,
)
def players_page(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user, server = (
        get_accessible_server(
            server_id,
            request,
            db,
        )
    )

    if not user:
        return RedirectResponse(
            "/login"
        )

    if not server or not has_permission(user, "players.view"):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    context = build_web_context(
        db,
        user,
        active_server=server,
    )

    context.update({
        "server": server,
        "page_title": "Players",
        "active_page": "players",
    })

    return render_page(
        request,
        "server_players.html",
        "partials/server_players.html",
        context,
    )


@router.get(
    "/api/web/servers/{server_id}/players"
)
def players_data(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user, server = (
        get_accessible_server(
            server_id,
            request,
            db,
        )
    )

    if not user:
        return JSONResponse(
            {
                "error":
                    "Not authenticated"
            },
            status_code=401,
        )

    if not server:
        return JSONResponse(
            {
                "error":
                    "Access denied"
            },
            status_code=403,
        )

    if not server or not has_permission(user, "players.view"):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    return get_player_data(
        server
    )


@router.post(
    "/api/web/servers/{server_id}/whitelist-enabled"
)
async def whitelist_enabled(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user, server = (
        get_accessible_server(
            server_id,
            request,
            db,
        )
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if not server or not has_permission(user, "players.manage"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )

    data = await request.json()

    enabled = bool(
        data.get(
            "enabled"
        )
    )

    try:

        set_whitelist_enabled(
            server,
            enabled,
        )

    except Exception as error:

        return JSONResponse(
            {"error": str(error)},
            status_code=400,
        )

    return {
        "success": True,
        "enabled": enabled,
    }


@router.post(
    "/api/web/servers/{server_id}/players/action"
)
async def player_action(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user, server = (
        get_accessible_server(
            server_id,
            request,
            db,
        )
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if not server or not has_permission(user, "players.manage"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )

    data = await request.json()

    player = (
        data.get(
            "player",
            ""
        )
        .strip()
    )

    action = (
        data.get(
            "action",
            ""
        )
        .strip()
    )


    if not player:

        return JSONResponse(
            {"error": "Player required"},
            status_code=400,
        )


    actions = {
        "whitelist":
            whitelist_player,

        "unwhitelist":
            remove_whitelist,

        "op":
            op_player,

        "deop":
            deop_player,

        "kick":
            kick_player,

        "ban":
            ban_player,

        "pardon":
            pardon_player,
    }


    handler = actions.get(
        action
    )

    if not handler:

        return JSONResponse(
            {"error": "Invalid action"},
            status_code=400,
        )


    try:

        handler(
            server,
            player,
        )

    except RuntimeError as error:

        return JSONResponse(
            {"error": str(error)},
            status_code=400,
        )


    return {
        "success": True
    }


@router.post("/api/web/servers/{server_id}/ip-bans/action")
async def ip_ban_action(server_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, "players.manage"):
        return JSONResponse({"error": "Access denied"}, status_code=403)
    data = await request.json()
    action = str(data.get("action", "")).strip()
    address = str(data.get("ip", "")).strip()
    handler = {"ban": ban_ip, "pardon": pardon_ip}.get(action)
    if not handler:
        return JSONResponse({"error": "Invalid action"}, status_code=400)
    try:
        handler(server, address)
    except RuntimeError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return {"success": True}
