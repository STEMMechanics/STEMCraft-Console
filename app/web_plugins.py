from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
)
import tempfile
from pathlib import Path

from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)

from sqlalchemy.orm import Session

from .database import get_db

from .plugin_manager import (
    disable_plugin,
    enable_plugin,
    list_plugins,
    remove_plugin,
    install_plugin_file,
    install_plugin_url,
    MAX_PLUGIN_BYTES,
    geyser_status,
    duplicate_plugin_groups,
    PluginFileExistsError,
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
from .processes import server_status


router = APIRouter()


def plugin_action_requires_restart(
    action: str,
    filenames: list[str],
    plugins: list[dict],
    running: bool,
) -> bool:
    """Return whether this mutation changes plugins loaded by a live server."""
    if not running:
        return False
    enabled = {
        plugin["filename"]: bool(plugin.get("enabled"))
        for plugin in plugins
    }
    if action == "enable":
        return any(enabled.get(filename) is False for filename in filenames)
    if action in {"disable", "remove"}:
        return any(enabled.get(filename) is True for filename in filenames)
    return False


def record_plugin_restart_requirement(db, server, required: bool) -> bool:
    if required and not server.plugins_dirty:
        server.plugins_dirty = True
        db.commit()
    return bool(server.plugins_dirty)


@router.post("/api/web/servers/{server_id}/plugins/upload")
async def upload_plugin(server_id: int, request: Request, plugin: UploadFile = File(), db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, "plugins.manage"):
        return JSONResponse({"error": "Administrator access required"}, status_code=403)
    filename = Path(plugin.filename or "").name
    replace = request.query_params.get("replace") == "true"
    try:
        with tempfile.NamedTemporaryFile(prefix="stemcraft-plugin-", suffix=".jar") as temporary:
            total = 0
            while chunk := await plugin.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_PLUGIN_BYTES:
                    raise ValueError("Plugin exceeds the configured size limit")
                temporary.write(chunk)
            temporary.flush()
            result = install_plugin_file(server, Path(temporary.name), filename, replace=replace)
        action_requires_restart = bool(server_status(server.id).get("running"))
        restart_required = record_plugin_restart_requirement(
            db, server, action_requires_restart,
        )
        return {
            "plugin": result,
            "restart_required": restart_required,
            "action_requires_restart": action_requires_restart,
            "duplicates": duplicate_plugin_groups(list_plugins(server)),
        }
    except PluginFileExistsError as error:
        return JSONResponse({
            "error": str(error),
            "code": "plugin_file_exists",
            "filename": error.filename,
            "enabled": error.enabled,
            "suppress_toast": True,
        }, status_code=409)
    except (ValueError, FileExistsError, OSError) as error:
        return JSONResponse({"error": str(error)}, status_code=400)


@router.post("/api/web/servers/{server_id}/plugins/url")
async def download_plugin(server_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, "plugins.manage"):
        return JSONResponse({"error": "Administrator access required"}, status_code=403)
    data = await request.json()
    try:
        result = install_plugin_url(
            server,
            str(data.get("url", "")).strip(),
            replace=data.get("replace") is True,
        )
        action_requires_restart = bool(server_status(server.id).get("running"))
        restart_required = record_plugin_restart_requirement(
            db, server, action_requires_restart,
        )
        return {
            "plugin": result,
            "restart_required": restart_required,
            "action_requires_restart": action_requires_restart,
            "duplicates": duplicate_plugin_groups(list_plugins(server)),
        }
    except PluginFileExistsError as error:
        return JSONResponse({
            "error": str(error),
            "code": "plugin_file_exists",
            "filename": error.filename,
            "enabled": error.enabled,
            "suppress_toast": True,
        }, status_code=409)
    except (ValueError, FileExistsError, OSError) as error:
        return JSONResponse({"error": str(error)}, status_code=400)


@router.get(
    "/servers/{server_id}/plugins",
    response_class=HTMLResponse,
)
def plugins_page(
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

    if not server or not has_permission(user, "plugins.view"):
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
        "page_title": "Plugins",
        "active_page": "plugins",
    })


    return render_page(
        request,
        "server_plugins.html",
        "partials/server_plugins.html",
        context,
    )


@router.get(
    "/api/web/servers/{server_id}/plugins"
)
def plugins_data(
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

    if not server or not has_permission(user, "plugins.view"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )


    plugins = list_plugins(server)

    return {
        "plugins": plugins,

        "geyser": geyser_status(server, plugins),

        "duplicates": duplicate_plugin_groups(plugins),

        "restart_required":
            server.plugins_dirty,

        "running":
            bool(server_status(server.id).get("running")),
    }


@router.post("/api/web/servers/{server_id}/plugins/duplicates/resolve")
async def resolve_plugin_duplicates(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, "plugins.manage"):
        return JSONResponse({"error": "Access denied"}, status_code=403)
    data = await request.json()
    filenames = data.get("disable")
    if not isinstance(filenames, list) or not all(isinstance(item, str) for item in filenames):
        return JSONResponse({"error": "Select valid plugin files"}, status_code=400)
    current_plugins = list_plugins(server)
    allowed = {
        plugin["filename"]
        for group in duplicate_plugin_groups(current_plugins)
        for plugin in group["plugins"]
    }
    selected = list(dict.fromkeys(filenames))
    if any(filename not in allowed for filename in selected):
        return JSONResponse({"error": "Plugin selection is no longer valid"}, status_code=409)
    try:
        for filename in selected:
            disable_plugin(server, filename)
    except (ValueError, FileNotFoundError, FileExistsError, OSError) as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    action_requires_restart = plugin_action_requires_restart(
        "disable", selected, current_plugins,
        bool(server_status(server.id).get("running")),
    )
    restart_required = record_plugin_restart_requirement(
        db, server, action_requires_restart,
    )
    return {
        "success": True,
        "message": f"Disabled {len(selected)} duplicate plugin file(s).",
        "restart_required": restart_required,
        "action_requires_restart": action_requires_restart,
        "duplicates": duplicate_plugin_groups(list_plugins(server)),
    }

@router.post(
    "/api/web/servers/{server_id}/plugins/action"
)
async def plugin_action(
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

    if not server or not has_permission(user, "plugins.manage"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )


    data = await request.json()

    filename = data.get("filename", "")
    filenames = data.get("filenames")
    if filenames is None:
        filenames = [filename]
    if not isinstance(filenames, list) or not filenames or not all(isinstance(item, str) for item in filenames):
        return JSONResponse({"error": "Select valid plugin files"}, status_code=400)
    filenames = list(dict.fromkeys(filenames))

    action = data.get(
        "action",
        "",
    )

    current_plugins = list_plugins(server)
    action_requires_restart = plugin_action_requires_restart(
        action, filenames, current_plugins,
        bool(server_status(server.id).get("running")),
    )


    try:

        if action == "enable":
            for filename in filenames:
                enable_plugin(server, filename)

        elif action == "disable":

            for filename in filenames:
                disable_plugin(server, filename)

        elif action == "remove":

            for filename in filenames:
                remove_plugin(server, filename, bool(data.get("remove_config")))

        else:

            return JSONResponse(
                {"error": "Invalid action"},
                status_code=400,
            )


    except (
        ValueError,
        FileNotFoundError,
        FileExistsError,
    ) as error:

        return JSONResponse(
            {"error": str(error)},
            status_code=400,
        )


    restart_required = record_plugin_restart_requirement(
        db, server, action_requires_restart,
    )

    return {
        "success": True,
        "restart_required": restart_required,
        "action_requires_restart": action_requires_restart,
        "affected": len(filenames),
    }
