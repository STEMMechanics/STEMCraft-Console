import hashlib
import secrets

from datetime import (
    datetime,
    timedelta,
)

from sqlalchemy.orm import Session

from .models import (
    PasswordResetToken,
    User,
)


RESET_MINUTES = 30


def hash_token(
    token: str,
) -> str:

    return hashlib.sha256(
        token.encode(
            "utf-8"
        )
    ).hexdigest()


def create_reset_token(
    db: Session,
    user: User,
) -> str:

    # Keep only one live reset credential per user. This bounds the number of
    # usable links if repeated requests are made or email delivery is delayed.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)

    token = secrets.token_urlsafe(
        32
    )

    record = PasswordResetToken(
        user_id=user.id,

        token_hash=hash_token(
            token
        ),

        expires_at=(
            datetime.utcnow()
            + timedelta(
                minutes=RESET_MINUTES
            )
        ),
    )

    db.add(record)
    db.commit()

    return token


def get_valid_reset(
    db: Session,
    token: str,
):

    token_hash = hash_token(
        token
    )

    record = (
        db.query(
            PasswordResetToken
        )
        .filter(
            PasswordResetToken.token_hash
            == token_hash,

            PasswordResetToken.used_at
            .is_(None),

            PasswordResetToken.expires_at
            > datetime.utcnow(),
        )
        .first()
    )

    return record
