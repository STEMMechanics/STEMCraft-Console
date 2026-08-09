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
from pathlib import Path

from .database import get_db

from .properties_manager import (
    get_properties_view,
    save_properties,
)
from .processes import (
    build_java_command,
    normalize_memory,
    register_server,
    resolve_server_jar,
    server_status,
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

    jar_files = []
    for path in Path(server.directory).glob("*.jar"):
        try:
            resolve_server_jar(server.directory, path.name)
        except ValueError:
            continue
        jar_files.append(path.name)

    return {
        "properties":
            get_properties_view(server),
        "startup": {
            "min_memory": server.min_memory,
            "max_memory": server.memory,
            "jar_name": server.jar_name,
            "java_args": server.java_args,
            "jar_files": sorted(jar_files),
            "command": build_java_command(
                server.memory,
                server.jar_name,
                server.java_args,
                server.min_memory,
            ),
        },
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
    error_field = None

    try:

        error_field = "min_memory"
        min_memory = normalize_memory(
            data.pop("min_memory", server.min_memory), "Initial RAM"
        )
        error_field = "max_memory"
        max_memory = normalize_memory(
            data.pop("max_memory", server.memory), "Maximum RAM"
        )
        jar_name = str(data.pop("jar_name", server.jar_name)).strip()
        java_args = str(data.pop("java_args", server.java_args)).strip()

        units = {"K": 1, "M": 1024, "G": 1024 * 1024}
        def memory_kib(value: str) -> int:
            return int(value[:-1]) * units[value[-1]]

        if memory_kib(min_memory) > memory_kib(max_memory):
            error_field = "min_memory"
            raise ValueError("Initial RAM cannot be greater than maximum RAM")

        # Validate syntax before touching the filesystem, then only inspect a
        # basename contained by the configured server directory.
        error_field = "jar_name"
        resolve_server_jar(server.directory, jar_name)
        error_field = "java_args"
        if len(java_args) > 1000:
            raise ValueError("Java startup options cannot exceed 1000 characters")
        build_java_command(max_memory, jar_name, java_args, min_memory)

        error_field = None
        save_properties(
            server,
            data,
        )

        server.min_memory = min_memory
        server.memory = max_memory
        server.jar_name = jar_name
        server.java_args = java_args

        # Keep DB copy of port in sync.
        if "server_port" in data:

            server.port = int(
                data["server_port"]
            )

        db.commit()

        register_server(server)

    except Exception as error:

        return JSONResponse(
            {"error": str(error), "field": error_field},
            status_code=400,
        )

    running = bool(server_status(server.id).get("running"))

    return {
        "success": True,
        "message": "Server properties saved.",
        "running": running,
        "restart_required": running,
    }
