from types import SimpleNamespace

from app.properties_manager import (
    read_properties,
    write_properties,
)


def test_read_properties(
    tmp_path,
):

    properties = (
        tmp_path
        / "server.properties"
    )

    properties.write_text(
        (
            "# Minecraft properties\n"
            "max-players=20\n"
            "pvp=true\n"
            "motd=Test Server\n"
        ),
        encoding="utf-8",
    )

    server = SimpleNamespace(
        directory=str(tmp_path)
    )

    result = read_properties(
        server
    )

    assert result["max-players"] == "20"
    assert result["pvp"] == "true"
    assert result["motd"] == "Test Server"


def test_write_properties_preserves_unknown_values(
    tmp_path,
):

    properties = (
        tmp_path
        / "server.properties"
    )

    properties.write_text(
        (
            "# Keep this comment\n"
            "max-players=20\n"
            "some-future-property=hello\n"
        ),
        encoding="utf-8",
    )

    server = SimpleNamespace(
        directory=str(tmp_path)
    )

    write_properties(
        server,
        {
            "max-players": "30",
        },
    )

    contents = properties.read_text(
        encoding="utf-8"
    )

    assert "max-players=30" in contents

    assert (
        "some-future-property=hello"
        in contents
    )

    assert (
        "# Keep this comment"
        in contents
    )