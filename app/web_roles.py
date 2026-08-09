from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import AccessRole, Permission
from .permissions import ALL_PERMISSIONS, has_permission
from .web_users import current_web_user


router = APIRouter()


def _role_json(role: AccessRole) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description or "",
        "system": role.system,
        "permissions": sorted(item.key for item in role.permissions),
        "user_count": len(role.users),
    }


def _role_manager(request: Request, db: Session):
    user = current_web_user(request, db)
    if not user:
        return None, JSONResponse({"error": "Not authenticated"}, status_code=401)
    if not has_permission(user, "roles.manage"):
        return None, JSONResponse({"error": "Role management permission required"}, status_code=403)
    return user, None


@router.get("/api/web/settings/roles/{role_id}")
def get_role(role_id: int, request: Request, db: Session = Depends(get_db)):
    _user, error = _role_manager(request, db)
    if error:
        return error
    role = db.get(AccessRole, role_id)
    if not role:
        return JSONResponse({"error": "Role not found"}, status_code=404)
    return _role_json(role)


@router.post("/api/web/settings/roles")
async def create_role(request: Request, db: Session = Depends(get_db)):
    _user, error = _role_manager(request, db)
    if error:
        return error
    data = await request.json()
    name = str(data.get("name", "")).strip()
    if len(name) < 2 or len(name) > 64:
        return JSONResponse({"error": "Role name must be 2 to 64 characters"}, status_code=400)
    if db.query(AccessRole).filter(AccessRole.name == name).first():
        return JSONResponse({"error": "Role name already exists"}, status_code=409)
    keys = set(data.get("permissions") or [])
    if not keys <= set(ALL_PERMISSIONS):
        return JSONResponse({"error": "Role contains an unknown permission"}, status_code=400)
    role = AccessRole(
        name=name,
        description=str(data.get("description", "")).strip() or None,
        permissions=db.query(Permission).filter(Permission.key.in_(keys)).all() if keys else [],
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return _role_json(role)


@router.post("/api/web/settings/roles/{role_id}")
async def update_role(role_id: int, request: Request, db: Session = Depends(get_db)):
    user, error = _role_manager(request, db)
    if error:
        return error
    role = db.get(AccessRole, role_id)
    if not role:
        return JSONResponse({"error": "Role not found"}, status_code=404)
    if role.name == "Administrator":
        return JSONResponse(
            {"error": "The Administrator role is immutable and always has full access"},
            status_code=403,
        )
    data = await request.json()
    name = str(data.get("name", role.name)).strip()
    existing = db.query(AccessRole).filter(AccessRole.name == name, AccessRole.id != role.id).first()
    if len(name) < 2 or len(name) > 64:
        return JSONResponse({"error": "Role name must be 2 to 64 characters"}, status_code=400)
    if role.system and name != role.name:
        return JSONResponse({"error": "Built-in roles cannot be renamed"}, status_code=400)
    if existing:
        return JSONResponse({"error": "Role name already exists"}, status_code=409)
    keys = set(data.get("permissions") or [])
    if not keys <= set(ALL_PERMISSIONS):
        return JSONResponse({"error": "Role contains an unknown permission"}, status_code=400)
    if user.role_id == role.id and not {"roles.manage", "users.manage"} <= keys:
        return JSONResponse({"error": "You cannot remove your own role management access"}, status_code=400)
    role.name = name
    role.description = str(data.get("description", "")).strip() or None
    role.permissions = db.query(Permission).filter(Permission.key.in_(keys)).all() if keys else []
    db.commit()
    return _role_json(role)


@router.delete("/api/web/settings/roles/{role_id}")
def delete_role(role_id: int, request: Request, db: Session = Depends(get_db)):
    _user, error = _role_manager(request, db)
    if error:
        return error
    role = db.get(AccessRole, role_id)
    if not role:
        return JSONResponse({"error": "Role not found"}, status_code=404)
    if role.system:
        return JSONResponse({"error": "Built-in roles cannot be deleted"}, status_code=400)
    if role.users:
        return JSONResponse({"error": "Move users to another role before deleting this role"}, status_code=409)
    db.delete(role)
    db.commit()
    return {"success": True}
