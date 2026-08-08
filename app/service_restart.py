import os
import threading
import time


RESTART_EXIT_CODE = 75


def _exit_for_systemd_restart(delay: float) -> None:
    time.sleep(delay)
    os._exit(RESTART_EXIT_CODE)


def schedule_console_restart(delay: float = 2.0) -> None:
    """Restart the console through systemd after the current response is sent."""
    if not os.environ.get("INVOCATION_ID"):
        raise RuntimeError(
            "Console restart is only available when the panel is running as a systemd service"
        )

    threading.Thread(
        target=_exit_for_systemd_restart,
        args=(delay,),
        daemon=True,
        name="console-systemd-restart",
    ).start()
