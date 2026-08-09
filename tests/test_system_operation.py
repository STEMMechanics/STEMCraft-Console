from app.system_operation import (
    begin_operation,
    clear_operation,
    current_operation,
    update_operation,
)


def setup_function():
    clear_operation()


def teardown_function():
    clear_operation()


def test_system_operation_is_shared_and_exclusive():
    started = begin_operation("update", "Updating", "Downloading", "installing")

    assert started["active"] is True
    assert current_operation()["kind"] == "update"
    assert begin_operation("restart", "Restarting", "Waiting", "restarting") is None


def test_system_operation_can_change_phase_and_clear():
    begin_operation("update", "Updating", "Downloading", "installing")

    update_operation(title="Restarting", message="Waiting", phase="restarting")

    operation = current_operation()
    assert operation["title"] == "Restarting"
    assert operation["message"] == "Waiting"
    assert operation["phase"] == "restarting"
    clear_operation()
    assert current_operation() is None
