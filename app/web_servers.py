import os

from pathlib import Path

from dotenv import load_dotenv

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)

from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from .database import get_db

from .models import (
    Server,
    User,
)

from .paper import (
    create_eula,
    create_server_properties,
    download_paper,
    get_versions,
    get_latest_build,
    get_builds,
)

from .processes import (
    get_console,
    restart_server,
    send_command,
    server_status,
    start_server,
    stop_server,
    register_server,
    MEMORY_PATTERN,
    SERVICE_PATTERN,
)
from .server_import import detect_server_directories, inspect_server_directory
from .server_deletion import delete_managed_server

from .web_context import (
    build_web_context,
)

from .web_render import (
    render_page,
)

from .web_users import (
    current_web_user,
)

from .processes import (
    server_process_stats,
)


load_dotenv(
    os.getenv(
        "STEMCRAFT_CONSOLE_ENV",
        ".env",
    )
)

router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)


SERVER_ROOT = Path(
    os.getenv(
        "STEMCRAFT_CONSOLE_SERVER_ROOT",
        "minecraft-servers",
    )
).expanduser().resolve()


SERVER_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


@router.post("/api/web/servers/{server_id}/delete")
async def web_delete_server(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_web_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if user.role != "admin":
        return JSONResponse({"error": "Admin required"}, status_code=403)

    server = db.get(Server, server_id)
    if not server:
        return JSONResponse({"error": "Server not found"}, status_code=404)

    data = await request.json()
    if data.get("confirmed") is not True:
        return JSONResponse(
            {"error": "Confirm the server deletion"},
            status_code=400,
        )

    try:
        return delete_managed_server(
            db,
            server,
            delete_files=data.get("delete_files") is True,
            server_root=SERVER_ROOT,
        )
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    except Exception as error:
        return JSONResponse({"error": f"Unable to delete server: {error}"}, status_code=500)

# -------------------------------------------------------------------
# Server access helper
# -------------------------------------------------------------------

def get_accessible_server(
    server_id: int,
    request: Request,
    db: Session,
):
    user = current_web_user(
        request,
        db,
    )

    if not user:
        return None, None

    server = db.get(
        Server,
        server_id,
    )

    if not server:
        return user, None

    if (
        user.role != "admin"
        and server not in user.servers
    ):
        return user, None

    register_server(server)

    return user, server


# -------------------------------------------------------------------
# Server list
# -------------------------------------------------------------------

@router.get(
    "/servers",
    response_class=HTMLResponse,
)
def servers_page(
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

    if user.role == "admin":

        servers = (
            db.query(Server)
            .order_by(Server.name)
            .all()
        )

    else:

        servers = user.servers

    return templates.TemplateResponse(
        request=request,
        name="servers.html",
        context={
            "user": user,
            "servers": servers,
        },
    )


# -------------------------------------------------------------------
# Create server
# -------------------------------------------------------------------

@router.get(
    "/servers/new",
    response_class=HTMLResponse,
)
def new_server_page(
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


    if user.role != "admin":

        return RedirectResponse(
            "/dashboard"
        )


    try:

        versions = get_versions()

    except Exception:

        versions = []


    context = build_web_context(
        db,
        user,
    )

    context.update({
        "page_title":
            "Create Server",

        "active_page":
            "servers",

        "versions":
            versions,
    })


    return render_page(
        request,
        "server_new.html",
        "partials/server_new.html",
        context,
    )

@router.post(
    "/servers/new"
)
def create_server_web(
    request: Request,

    name: str = Form(),

    minecraft_version: str = Form(),

    memory: str = Form(
        default="4G"
    ),

    process_backend: str = Form(
        default="systemd"
    ),

    port: int = Form(
        default=25565
    ),

    max_players: int = Form(
        default=20
    ),

    difficulty: str = Form(
        default="normal"
    ),

    gamemode: str = Form(
        default="survival"
    ),

    view_distance: int = Form(
        default=10
    ),

    simulation_distance: int = Form(
        default=10
    ),

    world_name: str = Form(
        default="world"
    ),

    seed: str = Form(
        default=""
    ),

    world_type: str = Form(
        default="minecraft:normal"
    ),

    generate_structures: bool = Form(
        default=False
    ),

    spawn_animals: bool = Form(
        default=False
    ),

    spawn_monsters: bool = Form(
        default=False
    ),

    spawn_npcs: bool = Form(
        default=False
    ),

    online_mode: bool = Form(
        default=False
    ),

    whitelist: bool = Form(
        default=False
    ),

    pvp: bool = Form(
        default=False
    ),

    enable_command_blocks: bool = Form(
        default=False
    ),

    motd: str = Form(
        default="A Minecraft Server"
    ),

    accept_eula: bool = Form(
        default=False
    ),

    db: Session = Depends(
        get_db
    ),
):

    user = current_web_user(
        request,
        db,
    )


    if not user:

        return RedirectResponse(
            "/login"
        )


    if user.role != "admin":

        return RedirectResponse(
            "/dashboard"
        )


    if not accept_eula:

        raise HTTPException(
            status_code=400,
            detail=(
                "You must accept the "
                "Minecraft EULA."
            ),
        )


    name = name.strip()

    world_name = (
        world_name.strip()
        or "world"
    )

    seed = seed.strip()

    motd = (
        motd.strip()
        or "A Minecraft Server"
    )


    if not name:

        raise HTTPException(
            status_code=400,
            detail="Server name required",
        )


    if not (
        1 <= port <= 65535
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid server port",
        )


    if not (
        1 <= max_players <= 1000
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid max players",
        )


    if not (
        2 <= view_distance <= 32
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid view distance",
        )


    if not (
        2 <= simulation_distance <= 32
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid simulation distance"
            ),
        )


    if difficulty not in (
        "peaceful",
        "easy",
        "normal",
        "hard",
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty",
        )


    if gamemode not in (
        "survival",
        "creative",
        "adventure",
        "spectator",
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid gamemode",
        )


    allowed_world_types = {
        "minecraft:normal",
        "minecraft:flat",
        "minecraft:large_biomes",
        "minecraft:amplified",
    }


    if (
        world_type
        not in allowed_world_types
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid world type",
        )


    existing = (
        db.query(Server)
        .filter(
            Server.name == name
        )
        .first()
    )


    if existing:

        raise HTTPException(
            status_code=409,
            detail=(
                "Server name already exists"
            ),
        )


    port_in_use = (
        db.query(Server)
        .filter(
            Server.port == port
        )
        .first()
    )


    if port_in_use:

        raise HTTPException(
            status_code=409,
            detail="Port already assigned",
        )


    slug = (
        name
        .lower()
        .replace(
            " ",
            "-",
        )
    )


    slug = "".join(
        character
        for character in slug
        if (
            character.isalnum()
            or character == "-"
        )
    )


    if not slug:

        raise HTTPException(
            status_code=400,
            detail="Invalid server name",
        )


    directory = (
        SERVER_ROOT
        / slug
    )


    if directory.exists():

        raise HTTPException(
            status_code=409,
            detail=(
                "Server directory "
                "already exists"
            ),
        )


    directory.mkdir(
        parents=True
    )


    try:

        result = download_paper(
            minecraft_version,
            str(directory),
        )


        create_eula(
            str(directory)
        )


        create_server_properties(
            directory=
                str(directory),

            port=
                port,

            max_players=
                max_players,

            difficulty=
                difficulty,

            gamemode=
                gamemode,

            view_distance=
                view_distance,

            simulation_distance=
                simulation_distance,

            world_name=
                world_name,

            seed=
                seed,

            world_type=
                world_type,

            generate_structures=
                generate_structures,

            spawn_animals=
                spawn_animals,

            spawn_monsters=
                spawn_monsters,

            spawn_npcs=
                spawn_npcs,

            online_mode=
                online_mode,

            whitelist=
                whitelist,

            pvp=
                pvp,

            enable_command_blocks=
                enable_command_blocks,

            motd=
                motd,
        )


        if process_backend not in {"subprocess", "systemd"}:
            raise ValueError("Invalid process backend")

        server = Server(
            name=name,

            directory=
                str(directory),

            service_name=
                slug,

            minecraft_version=
                result["version"],

            paper_build=
                result["build"],

            memory=
                memory,

            process_backend=
                process_backend,

            port=
                port,

            enabled=
                True,
        )


        db.add(
            server
        )

        db.commit()

        db.refresh(
            server
        )


    except Exception as error:

        import shutil

        shutil.rmtree(
            directory,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


    return RedirectResponse(
        f"/servers/{server.id}",
        status_code=303,
    )


# -------------------------------------------------------------------
# Import existing server
#
# Keep this static route above /servers/{server_id} so "import" can never
# be interpreted as a server identifier by the router.
# -------------------------------------------------------------------

@router.get(
    "/servers/import",
    response_class=HTMLResponse,
)
def import_servers_page(
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

    if user.role != "admin":
        return RedirectResponse(
            "/dashboard"
        )

    existing_dirs = {
        str(
            Path(
                server.directory
            ).resolve()
        )
        for server
        in db.query(Server).all()
    }

    detected = detect_server_directories(SERVER_ROOT, existing_dirs)

    context = build_web_context(
        db,
        user,
    )

    context.update({
        "detected_servers":
            detected,

        "page_title":
            "Import Server",

        "server_root": str(SERVER_ROOT),
    })

    return render_page(
        request,
        "server_import.html",
        "partials/server_import.html",
        context,
    )


# -------------------------------------------------------------------
# Server overview
# -------------------------------------------------------------------

@router.get(
    "/servers/{server_id:int}",
    response_class=HTMLResponse,
)
def server_detail(
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

    if not server:
        raise HTTPException(
            status_code=404,
            detail="Server not found",
        )


    context = build_web_context(
        db,
        user,
        active_server=server,
    )

    context.update({
        "server": server,
        "page_title": "Overview",
        "active_page": "overview",
    })


    return render_page(
        request,
        "server_detail.html",
        "partials/server_detail.html",
        context,
    )


# -------------------------------------------------------------------
# Server status
# -------------------------------------------------------------------

@router.get(
    "/api/web/servers/{server_id}/status"
)
def web_server_status(
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

    return server_status(
        server_id
    )


# -------------------------------------------------------------------
# Start
# -------------------------------------------------------------------

@router.post(
    "/api/web/servers/{server_id}/start"
)
def web_start_server(
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


    try:

        pid = start_server(
            server.id,
            server.directory,
            server.memory,
            server.jar_name,
            server.java_args,
        )


        # A successful start means pending
        # plugin changes have now been loaded.
        server.plugins_dirty = False

        db.commit()


        return {
            "success": True,
            "pid": pid,
        }


    except RuntimeError as error:

        return JSONResponse(
            {
                "error":
                    str(error)
            },
            status_code=400,
        )


    except Exception as error:

        return JSONResponse(
            {
                "error":
                    str(error)
            },
            status_code=500,
        )


# -------------------------------------------------------------------
# Stop
# -------------------------------------------------------------------

@router.post(
    "/api/web/servers/{server_id}/stop"
)
def web_stop_server(
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


    try:

        stop_server(
            server.id
        )

        return {
            "success": True
        }


    except RuntimeError as error:

        return JSONResponse(
            {
                "error":
                    str(error)
            },
            status_code=400,
        )


# -------------------------------------------------------------------
# Restart
# -------------------------------------------------------------------

@router.post(
    "/api/web/servers/{server_id}/restart"
)
def web_restart_server(
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


    try:

        pid = restart_server(
            server.id,
            server.directory,
            server.memory,
            server.jar_name,
            server.java_args,
        )


        # Restart loaded any changed plugins.
        server.plugins_dirty = False

        db.commit()


        return {
            "success": True,
            "pid": pid,
        }


    except RuntimeError as error:

        return JSONResponse(
            {
                "error":
                    str(error)
            },
            status_code=400,
        )


    except Exception as error:

        return JSONResponse(
            {
                "error":
                    str(error)
            },
            status_code=500,
        )


# -------------------------------------------------------------------
# Send console command
# -------------------------------------------------------------------

@router.post(
    "/api/web/servers/{server_id}/command"
)
async def web_command(
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


    data = await request.json()

    command = (
        data
        .get(
            "command",
            "",
        )
        .strip()
    )


    if not command:

        return JSONResponse(
            {
                "error":
                    "Command required"
            },
            status_code=400,
        )


    try:

        send_command(
            server.id,
            command,
        )

        return {
            "success": True
        }


    except RuntimeError as error:

        return JSONResponse(
            {
                "error":
                    str(error)
            },
            status_code=400,
        )


# -------------------------------------------------------------------
# Console data
# -------------------------------------------------------------------

@router.get(
    "/api/web/servers/{server_id}/console-data"
)
def web_console_data(
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


    status = server_status(
        server_id
    )

    running = status.get(
        "running",
        False,
    )


    # While running, use the live console
    # buffer owned by the panel.
    if running:

        return {
            "running": True,
            "source": "console",

            "lines":
                get_console(
                    server_id
                ),
        }


    # When stopped, fall back to latest.log.
    log_path = (
        Path(server.directory)
        / "logs"
        / "latest.log"
    )


    if not log_path.exists():

        return {
            "running": False,
            "source": "none",
            "lines": [],
        }


    try:

        lines = log_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        # Keep the response manageable.
        lines = lines[-500:]


    except OSError:

        lines = []


    return {
        "running": False,
        "source": "latest.log",
        "lines": lines,
    }


# -------------------------------------------------------------------
# Console page
# -------------------------------------------------------------------

@router.get(
    "/servers/{server_id:int}/console",
    response_class=HTMLResponse,
)
def console_page(
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

    if not server:
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
        "page_title": "Console",
        "active_page": "console",
    })


    return render_page(
        request,
        "console.html",
        "partials/console.html",
        context,
    )


@router.post("/api/web/servers/import/inspect")
async def inspect_import_path(request: Request, db: Session = Depends(get_db)):
    user = current_web_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if user.role != "admin":
        return JSONResponse({"error": "Admin required"}, status_code=403)
    data = await request.json()
    return inspect_server_directory(
        str(data.get("directory", "")),
        process_backend=str(data.get("process_backend", "systemd")),
    )


@router.post(
    "/servers/import"
)
def import_server(
    request: Request,

    directory: str = Form(),
    name: str = Form(),
    memory: str = Form(default="2G"),
    process_backend: str = Form(default="systemd"),

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

    if user.role != "admin":
        return RedirectResponse(
            "/dashboard"
        )


    if process_backend not in {"subprocess", "systemd"}:
        raise HTTPException(status_code=400, detail="Invalid process backend")
    if not MEMORY_PATTERN.fullmatch(memory):
        raise HTTPException(status_code=400, detail="Invalid memory allocation")

    inspection = inspect_server_directory(
        directory,
        process_backend=process_backend,
        verify_write=True,
    )
    if not inspection["ready"]:
        raise HTTPException(status_code=400, detail="; ".join(inspection["errors"]))
    directory_path = Path(inspection["directory"])
    jar_name = inspection["jar_name"]
    port = inspection["port"]


    existing = (
        db.query(Server)
        .filter(
            Server.directory
            == str(directory_path)
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail=(
                "Server is already imported"
            ),
        )


    service_name = re.sub(r"[^A-Za-z0-9_.@-]+", "-", directory_path.name).strip("-")[:128]
    if not SERVICE_PATTERN.fullmatch(service_name):
        raise HTTPException(status_code=400, detail="Directory cannot be converted to a valid service name")

    server = Server(
        name=name,

        directory=str(
            directory_path
        ),

        service_name=service_name,

        minecraft_version=None,

        paper_build=None,

        memory=memory,

        jar_name=jar_name,

        process_backend=process_backend,

        port=port,

        enabled=True,
    )


    db.add(server)
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Server name, directory, service name, or port is already managed") from error
    db.refresh(server)


    return RedirectResponse(
        f"/servers/{server.id}",
        status_code=303,
    )

@router.get("/api/web/servers/{server_id}/paper")
def web_paper_status(server_id: int, request: Request, version: str | None = None, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server:
        return JSONResponse({"error": "Access denied"}, status_code=403)
    try:
        versions = get_versions()
        current_version = server.minecraft_version
        latest_version = versions[0] if versions else current_version
        selected_version = version or current_version
        builds = get_builds(selected_version) if selected_version else []
        latest_build = builds[0] if builds else None
        latest_build_id = str(latest_build["id"]) if latest_build else None
        try:
            builds_behind = max(0, int(latest_build_id) - int(server.paper_build or latest_build_id))
        except (TypeError, ValueError):
            builds_behind = None
        return {
            "current_version": current_version,
            "current_build": server.paper_build,
            "latest_version": latest_version,
            "latest_build": latest_build_id,
            "builds_behind": builds_behind,
            "versions": versions,
            "selected_version": selected_version,
            "builds": [{"id": str(build["id"]), "channel": build.get("channel", "") } for build in builds],
            "running": server_status(server.id).get("running", False),
        }
    except Exception as error:
        return JSONResponse({"error": str(error)}, status_code=502)


@router.post("/api/web/servers/{server_id}/paper")
async def web_install_paper(server_id: int, request: Request, db: Session = Depends(get_db)):
    user, server = get_accessible_server(server_id, request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not server or user.role != "admin":
        return JSONResponse({"error": "Administrator access required"}, status_code=403)
    if server_status(server.id).get("running"):
        return JSONResponse({"error": "Stop the server before changing Paper"}, status_code=409)
    data = await request.json()
    version = str(data.get("version", "")).strip()
    try:
        build_id = int(data.get("build"))
    except (TypeError, ValueError):
        return JSONResponse({"error": "Select a valid Paper build"}, status_code=400)
    try:
        result = download_paper(version, server.directory, server.jar_name, build_id)
        server.minecraft_version = result["version"]
        server.paper_build = result["build"]
        db.commit()
        return result
    except (ValueError, OSError) as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    except Exception as error:
        return JSONResponse({"error": str(error)}, status_code=502)


@router.get(
    "/api/web/servers/{server_id}/process-stats"
)
def web_process_stats(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user, server = get_accessible_server(
        server_id,
        request,
        db,
    )

    if not user:
        return JSONResponse(
            {"error": "Not authenticated"},
            status_code=401,
        )

    if not server:
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )

    return server_process_stats(
        server.id
    )
