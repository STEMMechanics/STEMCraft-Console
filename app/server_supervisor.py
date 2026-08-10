"""Systemd-owned Minecraft process with a local Unix command socket."""

import argparse
import os
import signal
import socket
import subprocess
import threading
from pathlib import Path

from .processes import build_java_command, resolve_server_jar


def _serve_commands(server, process, stopping: threading.Event) -> None:
    while not stopping.is_set() and process.poll() is None:
        try:
            connection, _ = server.accept()
        except TimeoutError:
            continue
        except OSError:
            if stopping.is_set() or process.poll() is not None:
                return
            raise
        try:
            with connection:
                data = connection.recv(4096).decode("utf-8", "replace").strip()
                if data and "\n" not in data and process.stdin:
                    process.stdin.write((data + "\n").encode())
                    process.stdin.flush()
                    connection.sendall(b"ok\n")
        except OSError:
            if stopping.is_set() or process.poll() is not None:
                return
            raise


def supervise(directory: str, socket_path: str, memory: str, min_memory: str, jar_name: str, java_args: str, java_path: str = "java") -> int:
    root = Path(directory).resolve()
    resolve_server_jar(root, jar_name)
    endpoint = Path(socket_path)
    endpoint.parent.mkdir(parents=True, exist_ok=True)
    endpoint.unlink(missing_ok=True)
    process = subprocess.Popen(
        build_java_command(memory, jar_name, java_args, min_memory, java_path),
        cwd=root,
        stdin=subprocess.PIPE,
    )
    stopping = threading.Event()

    def request_stop(*_args):
        if stopping.is_set():
            return
        stopping.set()
        if process.poll() is None and process.stdin:
            process.stdin.write(b"stop\n")
            process.stdin.flush()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(endpoint))
    os.chmod(endpoint, 0o660)
    server.listen(8)
    server.settimeout(1)

    thread = threading.Thread(
        target=_serve_commands,
        args=(server, process, stopping),
        name="minecraft-command-socket",
    )
    thread.start()
    try:
        return process.wait()
    finally:
        # A clean Minecraft exit can race the socket thread's accept call. Stop
        # and join it before interpreter finalization so it cannot raise while
        # Python is tearing down buffered stderr (which turns a clean systemd
        # stop into SIGABRT and triggers Restart=on-failure).
        stopping.set()
        server.close()
        thread.join(timeout=2)
        endpoint.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-name")
    parser.add_argument("--directory")
    parser.add_argument("--socket")
    parser.add_argument("--memory", default="2G")
    parser.add_argument("--min-memory", default="2G")
    parser.add_argument("--jar", default="paper.jar")
    parser.add_argument("--java-args", default="")
    parser.add_argument("--java-path", default="java")
    options = parser.parse_args()
    if options.service_name:
        from .database import SessionLocal
        from .models import Server
        from .processes import SERVICE_PATTERN, SYSTEMD_SOCKET_DIR
        if not SERVICE_PATTERN.fullmatch(options.service_name):
            parser.error("invalid service name")
        db = SessionLocal()
        try:
            server = db.query(Server).filter(Server.service_name == options.service_name).one_or_none()
            if not server or server.process_backend != "systemd":
                parser.error("systemd server configuration not found")
            options.directory = server.directory
            options.memory = server.memory
            options.min_memory = server.min_memory
            options.jar = server.jar_name
            options.java_args = server.java_args
            options.java_path = server.java_path
            options.socket = str(SYSTEMD_SOCKET_DIR / f"{server.service_name}.sock")
        finally:
            db.close()
    if not options.directory or not options.socket:
        parser.error("directory and socket are required")
    raise SystemExit(supervise(options.directory, options.socket, options.memory, options.min_memory, options.jar, options.java_args, options.java_path))


if __name__ == "__main__":
    main()
