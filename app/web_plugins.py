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
    from .update_monitor import plugin_results
    for plugin, update in zip(plugins, plugin_results(db, server, plugins)):
        plugin["update"] = update

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


@router.post("/api/web/servers/{server_id}/plugins/check-updates")
def check_plugin_updates(server_id: int, request: Request, db: Session = Depends(get_db)):
    return _check_updates(server_id, request, db, "plugins", "plugins.manage")


@router.post("/api/web/servers/{server_id}/paper/check-updates")
def check_paper_updates(server_id: int, request: Request, db: Session = Depends(get_db)):
    return _check_updates(server_id, request, db, "paper", "servers.properties")


def _check_updates(server_id, request, db, scope, permission):
    from .update_monitor import check_updates, CheckInProgress
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, permission):
        return JSONResponse({"error": "Access denied"}, status_code=403)
    try:
        results = check_updates(db, [server], force=True, scope=scope)
        return {"updates": results[0][1]}
    except CheckInProgress as error:
        return JSONResponse({"error": str(error)}, status_code=409)


@router.get("/api/web/servers/{server_id}/paper/update-status")
def paper_update_status(server_id: int, request: Request, db: Session = Depends(get_db)):
    from .update_monitor import paper_result
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or not has_permission(user, "servers.view"):
        return JSONResponse({"error": "Access denied"}, status_code=403)
    return paper_result(db, server)


@router.post('/api/web/servers/{server_id}/plugins/monitoring')
async def save_plugin_monitoring(server_id: int, request: Request, db: Session = Depends(get_db)):
    from datetime import datetime
    from .models import UpdateMonitorLease
    from .plugin_monitoring import save_monitoring_config
    from .update_monitor import acquire_lease, CheckInProgress

    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({'error': 'Not authenticated'}, status_code=401)
    if not server or not has_permission(user, 'plugins.manage'):
        return JSONResponse({'error': 'Access denied'}, status_code=403)
    try:
        data = await request.json()
    except ValueError:
        return JSONResponse({'error': 'Invalid monitoring settings'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': 'Invalid monitoring settings'}, status_code=400)
    plugin = next((item for item in list_plugins(server) if item['filename'] == data.get('filename')), None)
    if not plugin:
        return JSONResponse({'error': 'Installed plugin not found; reload the Plugins page'}, status_code=404)
    try:
        acquire_lease(db, datetime.utcnow())
    except CheckInProgress as error:
        return JSONResponse({'error': str(error)}, status_code=409)
    try:
        save_monitoring_config(db, server.id, plugin['name'], data.get('mode'),
                               data.get('provider', ''), data.get('project', ''),
                               data.get('version_pattern', ''), data.get('link_pattern', ''), data.get('installed_pattern', ''))
        return {'success': True}
    except ValueError as error:
        return JSONResponse({'error': str(error)}, status_code=400)
    finally:
        db.rollback()
        db.query(UpdateMonitorLease).filter_by(id=1).update({'expires_at': datetime.min})
        db.commit()


@router.post('/api/web/servers/{server_id}/plugins/monitoring/preview')
async def preview_plugin_monitoring(server_id: int, request: Request, db: Session = Depends(get_db)):
    from datetime import datetime
    import json
    from types import SimpleNamespace
    from starlette.concurrency import run_in_threadpool
    from .models import UpdateMonitorLease
    from .plugin_monitoring import custom_provider
    from .update_monitor import acquire_lease, CheckInProgress, compare_release
    from .update_providers.http_source import SourceError

    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({'error': 'Not authenticated'}, status_code=401)
    if not server or not has_permission(user, 'plugins.manage'):
        return JSONResponse({'error': 'Access denied'}, status_code=403)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Invalid preview settings')
        plugin = next((item for item in list_plugins(server) if item['filename'] == data.get('filename')), None)
        if not plugin:
            return JSONResponse({'error': 'Installed plugin not found; reload the Plugins page'}, status_code=404)
        provider = custom_provider(data.get('provider'), data.get('project'), data.get('version_pattern', ''),
                                   data.get('link_pattern', ''), data.get('installed_pattern', ''))
    except ValueError as error:
        return JSONResponse({'error': str(error)}, status_code=400)
    now = datetime.utcnow()
    try:
        acquire_lease(db, now)
    except CheckInProgress as error:
        return JSONResponse({'error': str(error)}, status_code=409)
    try:
        releases = await run_in_threadpool(provider.fetch)
        row = SimpleNamespace(payload=json.dumps([release.to_dict() for release in releases]), checked_at=now, error=None)
        result = compare_release(plugin['name'], plugin.get('version'), provider, row, server.minecraft_version, filename=plugin['filename'])
        result['installed_comparison'], result['installed_comparison_source'] = provider.installed_details(plugin.get('version'), plugin['filename'])
        result['source_url'] = provider.project
        return result
    except SourceError as error:
        return JSONResponse({'error': str(error)}, status_code=400)
    except Exception:
        return JSONResponse({'error': 'Preview failed: the source was unavailable or returned invalid metadata'}, status_code=400)
    finally:
        db.rollback()
        db.query(UpdateMonitorLease).filter_by(id=1).update({'expires_at': datetime.min})
        db.commit()
