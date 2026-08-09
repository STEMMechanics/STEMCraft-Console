from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from .auth import (
    hash_password,
    require_users_manage,
)

from .database import get_db

from .models import AccessRole, User

from .schemas import (
    UserCreate,
    UserOut,
    UserUpdate,
)


router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=list[UserOut],
)
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_users_manage
    ),
):

    return (
        db.query(User)
        .order_by(User.username)
        .all()
    )


@router.post(
    "",
    response_model=UserOut,
    status_code=201,
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_users_manage
    ),
):

    existing = (
        db.query(User)
        .filter(
            User.username
            == payload.username
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Username already exists",
        )

    role = db.get(AccessRole, payload.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = User(
        username=payload.username,

        password_hash=hash_password(
            payload.password
        ),

        role="admin" if role.name == "Administrator" else "user",
        role_id=role.id,

        enabled=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/{user_id}",
    response_model=UserOut,
)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_users_manage
    ),
):

    user = db.get(
        User,
        user_id,
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if (
        user.id == admin.id
        and payload.role_id is not None
        and payload.role_id != user.role_id
    ):

        raise HTTPException(
            status_code=400,
            detail="You cannot remove your own admin access",
        )

    if payload.password is not None:

        user.password_hash = (
            hash_password(
                payload.password
            )
        )

    if payload.role_id is not None:
        role = db.get(AccessRole, payload.role_id)
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role_id = role.id
        user.role = "admin" if role.name == "Administrator" else "user"

    if payload.enabled is not None:
        user.enabled = payload.enabled

    db.commit()
    db.refresh(user)

    return user


@router.delete(
    "/{user_id}",
    status_code=204,
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_users_manage
    ),
):

    user = db.get(
        User,
        user_id,
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if user.id == admin.id:

        raise HTTPException(
            status_code=400,
            detail="You cannot delete yourself",
        )

    db.delete(user)
    db.commit()
