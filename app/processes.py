import subprocess
import os
import socket
import re
import shlex
import threading
import time
import psutil

from collections import deque
from pathlib import Path
from dataclasses import dataclass


processes: dict[int, subprocess.Popen] = {}

console_buffers: dict[int, deque] = {}

console_threads: dict[int, threading.Thread] = {}

# psutil calculates CPU usage from the difference between calls on the same
# Process object. Recreating it for every request makes every sample the first
# sample and therefore 0%.
stats_processes: dict[int, psutil.Process] = {}
stats_process_roots: dict[int, int] = {}


@dataclass
class ServerProcessConfig:
    backend: str
    service_name: str
    directory: str
    memory: str
    jar_name: str
    java_args: str


server_configs: dict[int, ServerProcessConfig] = {}
SERVICE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}$")
SYSTEMD_UNIT_PREFIX = os.getenv("STEMCRAFT_SYSTEMD_UNIT_PREFIX", "stemcraft-server@")
SYSTEMD_SOCKET_DIR = Path(os.getenv("STEMCRAFT_SYSTEMD_SOCKET_DIR", "/run/stemcraft-console"))


def register_server(server) -> None:
    backend = getattr(server, "process_backend", "subprocess") or "subprocess"
    if backend not in {"subprocess", "systemd"}:
        raise ValueError("Unsupported process backend")
    service_name = server.service_name
    if not SERVICE_PATTERN.fullmatch(service_name):
        raise ValueError("Invalid systemd service name")
    server_configs[server.id] = ServerProcessConfig(
        backend, service_name, server.directory, server.memory,
        server.jar_name, server.java_args,
    )


def _systemd_config(server_id: int) -> ServerProcessConfig | None:
    config = server_configs.get(server_id)
    return config if config and config.backend == "systemd" else None


def _systemctl(config: ServerProcessConfig, action: str, check: bool = True):
    if action not in {"start", "stop", "restart", "show"}:
        raise ValueError("Invalid systemctl action")
    unit = f"{SYSTEMD_UNIT_PREFIX}{config.service_name}.service"
    command = ["systemctl", action, unit]
    if action == "show":
        command.extend(["--property=ActiveState,MainPID", "--value"])
    return subprocess.run(command, capture_output=True, text=True, timeout=30, check=check)


def _systemd_status(config: ServerProcessConfig) -> dict:
    result = _systemctl(config, "show", check=False)
    if result.returncode != 0:
        return {"running": False, "pid": None, "backend": "systemd"}
    values = result.stdout.splitlines()
    active = values[0].strip() if values else "inactive"
    try:
        pid = int(values[1]) if len(values) > 1 and values[1] else None
    except ValueError:
        pid = None
    return {"running": active in {"active", "activating"}, "pid": pid, "backend": "systemd"}


MAX_CONSOLE_LINES = 1000


MEMORY_PATTERN = re.compile(r"^[1-9][0-9]*[KMGkmg]$")


def build_java_command(
    memory: str = "2G",
    jar_name: str = "paper.jar",
    java_args: str = "",
) -> list[str]:
    """Build a shell-free Java command from validated server settings."""
    if not MEMORY_PATTERN.fullmatch(memory):
        raise ValueError("Memory must look like 2G or 1024M")

    jar = Path(jar_name)
    if jar.name != jar_name or jar.suffix.lower() != ".jar":
        raise ValueError("JAR name must be a .jar file in the server directory")

    try:
        extra_args = shlex.split(java_args)
    except ValueError as error:
        raise ValueError("Invalid Java startup options") from error

    return [
        "java", f"-Xms{memory}", f"-Xmx{memory}",
        *extra_args, "-jar", jar_name, "--nogui",
    ]


def _read_console(
    server_id: int,
    process: subprocess.Popen,
):
    """
    Continuously read Minecraft stdout so the
    process cannot block and keep recent console
    lines in memory.
    """

    if server_id not in console_buffers:
        console_buffers[server_id] = deque(
            maxlen=MAX_CONSOLE_LINES
        )

    if not process.stdout:
        return

    try:
        for line in process.stdout:

            line = line.rstrip()

            console_buffers[
                server_id
            ].append(line)

    finally:
        return_code = process.poll()

        console_buffers[
            server_id
        ].append(
            f"[Panel] Server process exited "
            f"with code {return_code}"
        )


def start_server(
    server_id: int,
    directory: str,
    memory: str = "2G",
    jar_name: str = "paper.jar",
    java_args: str = "",
):
    config = _systemd_config(server_id)
    if config:
        if _systemd_status(config)["running"]:
            raise RuntimeError("Server is already running")
        _systemctl(config, "start")
        return _systemd_status(config).get("pid")
    existing = processes.get(
        server_id
    )

    if (
        existing
        and existing.poll() is None
    ):
        raise RuntimeError(
            "Server is already running"
        )

    directory_path = Path(
        directory
    )

    command = build_java_command(memory, jar_name, java_args)
    jar = directory_path / jar_name

    if not jar.exists():
        raise RuntimeError(
            f"{jar_name} does not exist"
        )

    console_buffers[server_id] = deque(
        maxlen=MAX_CONSOLE_LINES
    )

    console_buffers[
        server_id
    ].append(
        "[Panel] Starting server..."
    )

    process = subprocess.Popen(
        command,
        cwd=directory_path,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        stats_process = psutil.Process(process.pid)
        stats_process.cpu_percent(interval=None)
        stats_processes[server_id] = stats_process
    except psutil.Error:
        pass

    processes[
        server_id
    ] = process

    thread = threading.Thread(
        target=_read_console,
        args=(
            server_id,
            process,
        ),
        daemon=True,
    )

    thread.start()

    console_threads[
        server_id
    ] = thread

    return process.pid


def stop_server(
    server_id: int,
):
    config = _systemd_config(server_id)
    if config:
        if not _systemd_status(config)["running"]:
            raise RuntimeError("Server is not running")
        try:
            send_command(server_id, "stop")
        except RuntimeError:
            pass
        _systemctl(config, "stop")
        return
    process = processes.get(
        server_id
    )

    if (
        not process
        or process.poll() is not None
    ):
        raise RuntimeError(
            "Server is not running"
        )

    if not process.stdin:
        raise RuntimeError(
            "Server console unavailable"
        )

    console_buffers[
        server_id
    ].append(
        "[Panel] Stopping server..."
    )

    process.stdin.write(
        "stop\n"
    )

    process.stdin.flush()


def restart_server(
    server_id: int,
    directory: str,
    memory: str = "2G",
    jar_name: str = "paper.jar",
    java_args: str = "",
):
    config = _systemd_config(server_id)
    if config:
        _systemctl(config, "restart")
        return _systemd_status(config).get("pid")
    process = processes.get(
        server_id
    )

    if (
        process
        and process.poll() is None
    ):
        stop_server(
            server_id
        )

        try:
            process.wait(
                timeout=30
            )

        except subprocess.TimeoutExpired:

            process.kill()

            process.wait(
                timeout=5
            )

    return start_server(
        server_id,
        directory,
        memory,
        jar_name,
        java_args,
    )


def kill_server(
    server_id: int,
):
    process = processes.get(
        server_id
    )

    if not process:
        return

    if process.poll() is None:
        process.kill()

    processes.pop(
        server_id,
        None,
    )
    stats_processes.pop(server_id, None)
    stats_process_roots.pop(server_id, None)


def server_status(
    server_id: int,
):
    config = _systemd_config(server_id)
    if config:
        return _systemd_status(config)
    process = processes.get(
        server_id
    )

    if not process:

        return {
            "running": False,
            "pid": None,
        }

    return_code = (
        process.poll()
    )

    if return_code is not None:

        processes.pop(
            server_id,
            None,
        )
        stats_processes.pop(server_id, None)
        stats_process_roots.pop(server_id, None)

        return {
            "running": False,
            "pid": None,
            "exit_code":
                return_code,
        }

    return {
        "running": True,
        "pid": process.pid,
    }


def send_command(
    server_id: int,
    command: str,
):
    config = _systemd_config(server_id)
    if config:
        command = command.strip()
        if not command or "\n" in command or "\r" in command:
            raise RuntimeError("Invalid server command")
        endpoint = SYSTEMD_SOCKET_DIR / f"{config.service_name}.sock"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(5)
                client.connect(str(endpoint))
                client.sendall(command.encode("utf-8"))
                if client.recv(16).strip() != b"ok":
                    raise RuntimeError("Command was not accepted")
            return
        except OSError as error:
            raise RuntimeError("Systemd server console is unavailable") from error
    process = processes.get(
        server_id
    )

    if (
        not process
        or process.poll() is not None
    ):
        raise RuntimeError(
            "Server is not running"
        )

    if not process.stdin:
        raise RuntimeError(
            "Server console unavailable"
        )

    command = command.strip()

    if not command:
        return

    process.stdin.write(
        command + "\n"
    )

    process.stdin.flush()


def get_console(
    server_id: int,
):
    config = _systemd_config(server_id)
    if config:
        unit = f"{SYSTEMD_UNIT_PREFIX}{config.service_name}.service"
        result = subprocess.run(
            ["journalctl", "--unit", unit, "--lines", "500", "--no-pager", "--output", "cat"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return result.stdout.splitlines() if result.returncode == 0 else []
    buffer = console_buffers.get(
        server_id
    )

    if not buffer:
        return []

    return list(buffer)

def wait_for_console_message(
    server_id: int,
    texts,
    timeout: float = 10.0,
) -> bool:
    """
    Wait until a new console line contains
    any of the supplied text values.
    """

    import time

    if isinstance(
        texts,
        str,
    ):
        texts = [texts]

    wanted = [
        text.lower()
        for text in texts
    ]

    buffer = console_buffers.get(
        server_id
    )

    if buffer is None:
        return False

    start_index = len(buffer)

    deadline = (
        time.monotonic()
        + timeout
    )

    while (
        time.monotonic()
        < deadline
    ):

        current = list(
            console_buffers.get(
                server_id,
                []
            )
        )

        for line in current[
            start_index:
        ]:

            lower_line = (
                line.lower()
            )

            if any(
                text in lower_line
                for text in wanted
            ):
                return True

        time.sleep(0.1)

    return False


def server_process_stats(
    server_id: int,
):
    status = server_status(server_id)
    pid = status.get("pid")

    if not status.get("running") or not pid:
        stats_processes.pop(server_id, None)
        stats_process_roots.pop(server_id, None)
        return {
            "running": False,
            "cpu_percent": 0,
            "memory_used": 0,
            "memory_percent": 0,
        }

    try:
        proc = stats_processes.get(server_id)
        if proc is None or stats_process_roots.get(server_id) != pid:
            root_proc = psutil.Process(pid)
            proc = root_proc

            # A systemd service owns the lightweight Python supervisor as its
            # MainPID. Minecraft runs as a child, so measure that workload
            # instead of reporting the supervisor's near-zero CPU usage.
            if _systemd_config(server_id):
                children = root_proc.children(recursive=True)
                if children:
                    proc = children[-1]

            proc.cpu_percent(interval=None)
            stats_processes[server_id] = proc
            stats_process_roots[server_id] = pid

        memory = proc.memory_info()

        return {
            "running": True,

            "cpu_percent":
                round(
                    proc.cpu_percent(
                        interval=None
                    ),
                    1,
                ),

            "memory_used":
                memory.rss,

            "memory_percent":
                round(
                    proc.memory_percent(),
                    1,
                ),
        }

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
    ):

        stats_processes.pop(server_id, None)
        stats_process_roots.pop(server_id, None)

        return {
            "running": False,
            "cpu_percent": 0,
            "memory_used": 0,
            "memory_percent": 0,
        }
