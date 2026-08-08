from datetime import datetime, timedelta, timezone

from fastapi import (
    Depends,
    HTTPException,
    status,
)

from fastapi.security import OAuth2PasswordBearer

from jose import JWTError, jwt

from pwdlib import PasswordHash

from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .config import SECRET_KEY


ALGORITHM = "HS256"

TOKEN_HOURS = 12


password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        password,
        hashed_password,
    )


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user.id),

        "username": user.username,

        "role": user.role,

        "iat": now,

        "exp": now + timedelta(
            hours=TOKEN_HOURS
        ),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):

    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = int(
            payload.get("sub")
        )

    except (
        JWTError,
        ValueError,
        TypeError,
    ):
        raise auth_error

    user = db.get(
        User,
        user_id,
    )

    if not user:
        raise auth_error

    if not user.enabled:
        raise auth_error

    return user


def require_admin(
    user: User = Depends(
        get_current_user
    ),
):

    if user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )

    return user
