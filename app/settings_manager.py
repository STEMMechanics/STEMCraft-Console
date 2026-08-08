from sqlalchemy.orm import Session

from .models import AppSetting


SMTP_DEFAULTS = {
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_username": "",
    "smtp_password": "",
    "smtp_security": "starttls",
    "smtp_from_name": "STEMCraft Console",
    "smtp_from_address": "",
}


def get_setting(
    db: Session,
    key: str,
    default: str = "",
) -> str:

    setting = (
        db.query(AppSetting)
        .filter(
            AppSetting.key == key
        )
        .first()
    )

    if not setting:
        return default

    return setting.value or ""


def set_setting(
    db: Session,
    key: str,
    value: str,
):

    setting = (
        db.query(AppSetting)
        .filter(
            AppSetting.key == key
        )
        .first()
    )

    if not setting:

        setting = AppSetting(
            key=key,
            value=value,
        )

        db.add(setting)

    else:

        setting.value = value


def get_smtp_settings(
    db: Session,
) -> dict:

    return {
        key:
            get_setting(
                db,
                key,
                default,
            )
        for key, default
        in SMTP_DEFAULTS.items()
    }


def save_smtp_settings(
    db: Session,
    data: dict,
):

    for key, default in SMTP_DEFAULTS.items():

        value = str(
            data.get(
                key,
                default,
            )
        )

        set_setting(
            db,
            key,
            value,
        )

    db.commit()