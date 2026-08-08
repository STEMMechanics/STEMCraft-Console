import json
import re
import ipaddress

from pathlib import Path

from .processes import (
    get_console,
    send_command,
    server_status,
)


JOIN_PATTERN = re.compile(
    r": ([A-Za-z0-9_]{1,16}) joined the game"
)

LEAVE_PATTERN = re.compile(
    r": ([A-Za-z0-9_]{1,16}) left the game"
)


def read_json_file(
    path: Path,
    default,
):
    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return default


def read_properties(
    directory: str,
) -> dict:

    path = (
        Path(directory)
        / "server.properties"
    )

    properties = {}

    if not path.exists():
        return properties

    for line in path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines():

        line = line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, value = line.split(
            "=",
            1,
        )

        properties[key.strip()] = (
            value.strip()
        )

    return properties


def set_property(
    directory: str,
    key: str,
    value: str,
):
    path = (
        Path(directory)
        / "server.properties"
    )

    lines = []

    found = False

    if path.exists():

        lines = path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()

    output = []

    for line in lines:

        if line.startswith(
            key + "="
        ):

            output.append(
                f"{key}={value}"
            )

            found = True

        else:
            output.append(line)

    if not found:
        output.append(
            f"{key}={value}"
        )

    path.write_text(
        "\n".join(output) + "\n",
        encoding="utf-8",
    )


def get_online_players(
    server_id: int,
) -> set[str]:
    """
    Reconstruct online state from this
    panel session's console buffer.

    Later on Ubuntu we can replace this
    with a stronger runtime query.
    """

    status = server_status(
        server_id
    )

    if not status.get(
        "running",
        False,
    ):
        return set()

    online = set()

    for line in get_console(
        server_id
    ):

        joined = (
            JOIN_PATTERN.search(line)
        )

        if joined:

            online.add(
                joined.group(1)
            )

            continue

        left = (
            LEAVE_PATTERN.search(line)
        )

        if left:

            online.discard(
                left.group(1)
            )

    return online


def get_player_data(
    server,
) -> dict:

    root = Path(
        server.directory
    )

    properties = read_properties(
        server.directory
    )

    whitelist_data = read_json_file(
        root / "whitelist.json",
        [],
    )

    ops_data = read_json_file(
        root / "ops.json",
        [],
    )

    banned_data = read_json_file(
        root / "banned-players.json",
        [],
    )

    ip_bans = read_json_file(
        root / "banned-ips.json",
        [],
    )

    user_cache = read_json_file(
        root / "usercache.json",
        [],
    )


    whitelist = {
        item.get("name", "").casefold():
            item
        for item in whitelist_data
        if item.get("name")
    }

    operators = {
        item.get("name", "").casefold():
            item
        for item in ops_data
        if item.get("name")
    }

    banned = {
        item.get("name", "").casefold():
            item
        for item in banned_data
        if item.get("name")
    }

    cache = {
        item.get("name", "").casefold():
            item
        for item in user_cache
        if item.get("name")
    }


    online_names = get_online_players(
        server.id
    )

    online = {
        name.casefold(): name
        for name in online_names
    }


    names = set()

    names.update(cache)
    names.update(whitelist)
    names.update(operators)
    names.update(banned)
    names.update(online)


    players = []

    for key in names:

        cached = cache.get(
            key,
            {}
        )

        whitelist_entry = (
            whitelist.get(
                key,
                {}
            )
        )

        op_entry = (
            operators.get(
                key,
                {}
            )
        )

        banned_entry = (
            banned.get(
                key,
                {}
            )
        )

        name = (
            online.get(key)
            or cached.get("name")
            or whitelist_entry.get("name")
            or op_entry.get("name")
            or banned_entry.get("name")
            or key
        )

        uuid = (
            cached.get("uuid")
            or whitelist_entry.get("uuid")
            or op_entry.get("uuid")
            or banned_entry.get("uuid")
        )

        players.append({
            "name": name,
            "uuid": uuid,

            "online":
                key in online,

            "whitelisted":
                key in whitelist,

            "operator":
                key in operators,

            "op_level":
                op_entry.get(
                    "level",
                    None,
                ),

            "banned":
                key in banned,

            "ban_reason":
                banned_entry.get(
                    "reason"
                ),
        })


    players.sort(
        key=lambda item: (
            not item["online"],
            item["name"].lower(),
        )
    )


    max_players = 20

    try:
        max_players = int(
            properties.get(
                "max-players",
                "20",
            )
        )

    except ValueError:
        pass


    whitelist_enabled = (
        properties.get(
            "white-list",
            "false",
        ).lower()
        == "true"
    )


    return {
        "running":
            server_status(
                server.id
            ).get(
                "running",
                False,
            ),

        "online_count":
            len(online_names),

        "max_players":
            max_players,

        "whitelist_enabled":
            whitelist_enabled,

        "whitelisted_count":
            len(whitelist),

        "operator_count":
            len(operators),

        "banned_count":
            len(banned),

        "ip_banned_count":
            len(ip_bans),

        "ip_bans": [
            {
                "ip": str(item.get("ip", "")),
                "reason": item.get("reason"),
                "source": item.get("source"),
                "created": item.get("created"),
                "expires": item.get("expires"),
            }
            for item in ip_bans
            if item.get("ip")
        ],

        "players":
            players,
    }


def set_whitelist_enabled(
    server,
    enabled: bool,
):
    set_property(
        server.directory,
        "white-list",
        "true"
        if enabled
        else "false",
    )

    if server_status(
        server.id
    ).get("running"):

        send_command(
            server.id,
            (
                "whitelist on"
                if enabled
                else "whitelist off"
            ),
        )


def require_running(
    server,
):
    if not server_status(
        server.id
    ).get(
        "running",
        False,
    ):
        raise RuntimeError(
            "Server must be running "
            "for this action."
        )


def whitelist_player(
    server,
    player: str,
):
    require_running(server)

    send_command(
        server.id,
        f"whitelist add {player}",
    )


def remove_whitelist(
    server,
    player: str,
):
    require_running(server)

    send_command(
        server.id,
        f"whitelist remove {player}",
    )


def op_player(
    server,
    player: str,
):
    require_running(server)

    send_command(
        server.id,
        f"op {player}",
    )


def deop_player(
    server,
    player: str,
):
    require_running(server)

    send_command(
        server.id,
        f"deop {player}",
    )


def kick_player(
    server,
    player: str,
):
    require_running(server)

    send_command(
        server.id,
        f"kick {player}",
    )


def ban_player(
    server,
    player: str,
):
    require_running(server)

    send_command(
        server.id,
        f"ban {player}",
    )


def pardon_player(
    server,
    player: str,
):
    require_running(server)

    send_command(
        server.id,
        f"pardon {player}",
    )


def ban_ip(server, address: str):
    require_running(server)
    try:
        normalized = str(ipaddress.ip_address(address.strip()))
    except ValueError as error:
        raise RuntimeError("A valid IPv4 or IPv6 address is required") from error
    send_command(server.id, f"ban-ip {normalized}")


def pardon_ip(server, address: str):
    require_running(server)
    try:
        normalized = str(ipaddress.ip_address(address.strip()))
    except ValueError as error:
        raise RuntimeError("A valid IPv4 or IPv6 address is required") from error
    send_command(server.id, f"pardon-ip {normalized}")
