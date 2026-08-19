from app import java_runtime
from app.processes import build_java_command


def test_recommended_java_tracks_paper_requirements():
    assert java_runtime.recommended_java_major("26.2") == 25
    assert java_runtime.recommended_java_major("1.21.11") == 21
    assert java_runtime.recommended_java_major("1.18.2") == 17
    assert java_runtime.recommended_java_major("1.16.5") == 16
    assert java_runtime.recommended_java_major("1.12.2") == 11
    assert java_runtime.recommended_java_major("1.8.9") == 8


def test_java_runtime_is_part_of_shell_free_startup_command():
    command = build_java_command(
        "4G", "paper.jar", "", "2G", "/usr/lib/jvm/java-25/bin/java"
    )

    assert command == [
        "/usr/lib/jvm/java-25/bin/java", "-Xms2G", "-Xmx4G",
        "-jar", "paper.jar", "--nogui",
    ]


def test_select_java_runtime_prefers_exact_recommendation():
    runtimes = [
        {"path": "/java/25", "major": 25},
        {"path": "/java/21", "major": 21},
    ]

    assert java_runtime.select_java_runtime(runtimes, "26.2") == "/java/25"
    assert java_runtime.select_java_runtime(runtimes, "1.21.11") == "/java/21"


def test_reconcile_java_path_replaces_updated_jdk_with_same_major():
    runtimes = [
        {"path": "/usr/lib/jvm/jdk-25.0.5-oracle-aarch64/bin/java", "major": 25},
        {"path": "/usr/lib/jvm/java-21-openjdk/bin/java", "major": 21},
    ]

    assert java_runtime.reconcile_java_path(
        "/usr/lib/jvm/jdk-25.0.4-oracle-aarch64/bin/java", runtimes, "1.21.11",
    ) == "/usr/lib/jvm/jdk-25.0.5-oracle-aarch64/bin/java"


def test_reconcile_java_path_keeps_an_available_runtime():
    runtimes = [{"path": "/java/21", "major": 21}]

    assert java_runtime.reconcile_java_path(
        "/java/21", runtimes, "26.2",
    ) == "/java/21"


def test_server_form_runtime_choices_do_not_expose_paths_or_vendor_details():
    runtimes = [
        {"path": "/secret/java-25-a", "major": 25, "name": "Vendor A"},
        {"path": "/secret/java-25-b", "major": 25, "name": "Vendor B"},
        {"path": "/secret/java-21", "major": 21, "name": "Vendor C"},
    ]

    assert java_runtime.java_runtime_choices(runtimes) == [
        {"major": 25, "label": "Java 25"},
        {"major": 21, "label": "Java 21"},
    ]
