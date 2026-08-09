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

from .properties_manager import (
    get_properties_view,
    save_properties,
)

from .web_context import (
    build_web_context,
)

from .web_render import (
    render_page,
)

from .web_servers import (
    get_accessible_server,
)
from .permissions import has_permission


router = APIRouter()


@router.get(
    "/servers/{server_id}/properties",
    response_class=HTMLResponse,
)
def properties_page(
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

    if not server or not has_permission(user, "servers.properties"):
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
        "page_title": "Properties",
        "active_page": "properties",
    })

    return render_page(
        request,
        "server_properties.html",
        "partials/server_properties.html",
        context,
    )


@router.get(
    "/api/web/servers/{server_id}/properties"
)
def properties_data(
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

    if not server or not has_permission(user, "servers.properties"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )

    return {
        "properties":
            get_properties_view(server),
    }


@router.post(
    "/api/web/servers/{server_id}/properties"
)
async def save_properties_api(
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

    if not server or not has_permission(user, "servers.properties"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )

    data = await request.json()

    try:

        save_properties(
            server,
            data,
        )

        # Keep DB copy of port in sync.
        if "server_port" in data:

            server.port = int(
                data["server_port"]
            )

            db.commit()

    except Exception as error:

        return JSONResponse(
            {"error": str(error)},
            status_code=400,
        )

    return {
        "success": True,
        "restart_required": True,
    }
