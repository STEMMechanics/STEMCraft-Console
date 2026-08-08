import os
import secrets
import warnings


def _session_secret() -> str:
    configured = os.getenv("STEMCRAFT_CONSOLE_SECRET")
    if configured:
        if len(configured) < 32:
            warnings.warn(
                "STEMCRAFT_CONSOLE_SECRET should contain at least 32 characters",
                RuntimeWarning,
                stacklevel=2,
            )
        return configured

    warnings.warn(
        "STEMCRAFT_CONSOLE_SECRET is not set; using a temporary secret. "
        "Sessions and API tokens will be invalidated when the app restarts.",
        RuntimeWarning,
        stacklevel=2,
    )
    return secrets.token_urlsafe(48)


SECRET_KEY = _session_secret()
COOKIE_SECURE = os.getenv(
    "STEMCRAFT_CONSOLE_COOKIE_SECURE", "false"
).lower() in {"1", "true", "yes", "on"}
MAX_UPLOAD_BYTES = int(
    os.getenv("STEMCRAFT_CONSOLE_MAX_UPLOAD_BYTES", str(512 * 1024 * 1024))
)
