import threading

from app.server_supervisor import _serve_commands


class ExitedProcess:
    stdin = None

    def poll(self):
        return 0


class ClosedSocket:
    def accept(self):
        raise AssertionError("accept should not run after the process exits")


def test_command_thread_exits_cleanly_after_minecraft_stops():
    thread = threading.Thread(
        target=_serve_commands,
        args=(ClosedSocket(), ExitedProcess(), threading.Event()),
    )

    thread.start()
    thread.join(timeout=1)

    assert not thread.is_alive()


class ClosingSocket:
    def __init__(self, stopping):
        self.stopping = stopping

    def accept(self):
        self.stopping.set()
        raise OSError("socket closed")


class RunningProcess:
    stdin = None

    def poll(self):
        return None


def test_command_thread_ignores_socket_close_during_shutdown():
    stopping = threading.Event()

    _serve_commands(ClosingSocket(stopping), RunningProcess(), stopping)
