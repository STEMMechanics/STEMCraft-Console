import shutil

import psutil

from fastapi import (
    APIRouter,
    Depends,
)

from .auth import get_current_user
from .models import User


router = APIRouter(
    prefix="/system",
    tags=["System"],
)


def bytes_to_gb(value: int) -> float:
    return round(
        value / 1024 / 1024 / 1024,
        1,
    )


@router.get("/stats")
def system_stats(
    user: User = Depends(
        get_current_user
    ),
):
    memory = psutil.virtual_memory()

    disk = shutil.disk_usage("/")

    cpu_percent = psutil.cpu_percent(
        interval=None
    )

    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(),
        },

        "memory": {
            "used": bytes_to_gb(
                memory.used
            ),
            "total": bytes_to_gb(
                memory.total
            ),
            "percent": memory.percent,
        },

        "storage": {
            "used": bytes_to_gb(
                disk.used
            ),
            "total": bytes_to_gb(
                disk.total
            ),
            "percent": round(
                disk.used
                / disk.total
                * 100,
                1,
            ),
        },
    }