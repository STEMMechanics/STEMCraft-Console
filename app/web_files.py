from pathlib import Path
import tempfile
import zipfile
from urllib.parse import quote
from starlette.background import BackgroundTask

from .file_manager import (
    create_folder,
    delete_entry,
    list_directory,
    move_entry,
    read_text_file,
    rename_entry,
    safe_path,
    write_text_file,
)
from .config import MAX_UPLOAD_BYTES

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)

from sqlalchemy.orm import Session

from .database import get_db

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
    "/servers/{server_id}/files",
    response_class=HTMLResponse,
)
def files_page(
    server_id: int,
    request: Request,
    path: str = "",
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

    if not server or not has_permission(user, "files.view"):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )


    try:
        data = list_directory(
            server,
            path,
        )

    except (
        ValueError,
        FileNotFoundError,
    ) as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


    context = build_web_context(
        db,
        user,
        active_server=server,
    )

    context.update({
        "server": server,
        "page_title": "Files",
        "active_page": "files",
        **data,
    })


    return render_page(
        request,
        "server_files.html",
        "partials/server_files.html",
        context,
    )


@router.post(
    "/servers/{server_id}/files/upload"
)
async def upload_file(
    server_id: int,
    request: Request,

    path: str = Form(
        default=""
    ),

    file: UploadFile = File(...),

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

    if not server or not has_permission(user, "files.manage"):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )


    directory = safe_path(
        server,
        path,
    )


    filename = Path(
        file.filename or ""
    ).name

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )


    destination = (
        directory / filename
    )


    written = 0
    try:
        with destination.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Uploaded file is too large",
                    )
                output.write(chunk)
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail="A file with that name already exists",
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


    return RedirectResponse(
        (
            f"/servers/{server_id}/files"
            f"?path={path}"
        ),
        status_code=303,
    )


@router.get(
    "/servers/{server_id}/files/download"
)
def download_file(
    server_id: int,
    request: Request,
    path: str,
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
        raise HTTPException(
            status_code=401
        )

    if not server or not has_permission(user, "files.view"):
        raise HTTPException(
            status_code=403
        )


    target = safe_path(
        server,
        path,
    )

    if not target.is_file() and not target.is_dir():

        raise HTTPException(
            status_code=404,
            detail="File or folder not found",
        )


    if target.is_file():
        return FileResponse(target, filename=target.name)

    temporary = tempfile.NamedTemporaryFile(
        prefix="stemcraft-folder-", suffix=".zip", delete=False,
    )
    temporary.close()
    archive_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in target.rglob("*"):
                if item.is_symlink() or not item.is_file():
                    continue
                archive.write(item, item.relative_to(target.parent))
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise
    return FileResponse(
        archive_path,
        filename=f"{target.name}.zip",
        media_type="application/zip",
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@router.get(
    "/servers/{server_id}/files/edit",
    response_class=HTMLResponse,
)
def edit_file_page(
    server_id: int,
    request: Request,
    path: str,
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

    if not server or not has_permission(user, "files.manage"):
        raise HTTPException(
            status_code=403
        )


    try:
        contents = read_text_file(
            server,
            path,
        )

    except (
        ValueError,
        FileNotFoundError,
    ) as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


    context = build_web_context(
        db,
        user,
        active_server=server,
    )

    context.update({
        "server": server,
        "page_title": "Edit File",
        "file_path": path,
        "filename":
            Path(path).name,
        "contents": contents,
        "parent_path": "" if str(Path(path).parent) == "." else str(Path(path).parent),
    })


    return render_page(
        request,
        "file_edit.html",
        "partials/file_edit.html",
        context,
    )


@router.post(
    "/servers/{server_id}/files/edit"
)
def save_file(
    server_id: int,
    request: Request,

    path: str = Form(),
    contents: str = Form(),
    close: bool = Form(default=False),

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

    if not server or not has_permission(user, "files.manage"):
        raise HTTPException(
            status_code=403
        )


    write_text_file(
        server,
        path,
        contents,
    )


    parent = str(
        Path(path).parent
    )

    if parent == ".":
        parent = ""


    destination = (
        f"/servers/{server_id}/files?path={quote(parent)}"
        if close else
        f"/servers/{server_id}/files/edit?path={quote(path)}&saved=true"
    )
    return RedirectResponse(destination, status_code=303)


@router.post(
    "/api/web/servers/{server_id}/files/mkdir"
)
async def mkdir(
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

    if not server or not has_permission(user, "files.manage"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )


    data = await request.json()


    try:

        create_folder(
            server,
            data.get(
                "path",
                "",
            ),
            data.get(
                "name",
                "",
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


@router.post(
    "/api/web/servers/{server_id}/files/rename"
)
async def rename(
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

    if not server or not has_permission(user, "files.manage"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )


    data = await request.json()


    try:

        rename_entry(
            server,
            data.get(
                "path",
                "",
            ),
            data.get(
                "name",
                "",
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


@router.post(
    "/api/web/servers/{server_id}/files/delete"
)
async def delete(
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

    if not server or not has_permission(user, "files.manage"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )


    data = await request.json()


    try:

        delete_entry(
            server,
            data.get(
                "path",
                "",
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

@router.post(
    "/api/web/servers/{server_id}/files/move"
)
async def move(
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

    if not server or not has_permission(user, "files.manage"):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403,
        )

    data = await request.json()

    try:
        move_entry(
            server,
            data.get(
                "source",
                "",
            ),
            data.get(
                "destination",
                "",
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
