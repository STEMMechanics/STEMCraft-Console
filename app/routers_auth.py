from fastapi.security import OAuth2PasswordRequestForm

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    get_current_user,
    verify_password,
)

from .database import get_db

from .models import User

from .schemas import (
    TokenResponse,
    UserOut,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(
            User.username == form_data.username
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    if not user.enabled:
        raise HTTPException(
            status_code=401,
            detail="Account disabled",
        )

    if not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    if user.totp_enabled:
        raise HTTPException(
            status_code=403,
            detail="Complete two-factor authentication through the web login",
        )

    if user.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="Change your password through the web login before using the API",
        )

    return TokenResponse(
        access_token=create_access_token(user)
    )

@router.get(
    "/me",
    response_model=UserOut,
)
def me(
    user: User = Depends(
        get_current_user
    ),
):

    return user
