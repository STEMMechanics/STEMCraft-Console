import re
import zipfile
import ipaddress
import os
import socket
import urllib.parse
import urllib.request
import shutil
import tempfile

from pathlib import Path


MAX_PLUGIN_BYTES = int(os.getenv("STEMCRAFT_MAX_PLUGIN_BYTES", str(128 * 1024 * 1024)))


def plugins_directory(server) -> Path:
    return Path(server.directory) / "plugins"


def read_plugin_yml(jar_path: Path) -> dict:
    """
    Read the small amount of metadata we need
    from plugin.yml inside a Paper/Spigot plugin.
    """

    try:
        with zipfile.ZipFile(jar_path) as jar:

            with jar.open("plugin.yml") as file:
                text = file.read().decode(
                    "utf-8",
                    errors="ignore",
                )

    except (
        OSError,
        KeyError,
        zipfile.BadZipFile,
    ):
        return {}


    result = {}

    for line in text.splitlines():

        match = re.match(
            r"^(name|version):\s*[\"']?(.*?)[\"']?\s*$",
            line.strip(),
            re.IGNORECASE,
        )

        if match:
            result[
                match.group(1).lower()
            ] = match.group(2)

    return result


def plugin_config_directory(
    jar_path: Path,
) -> Path | None:

    metadata = read_plugin_yml(
        jar_path
    )

    name = metadata.get("name")

    if not name:
        return None

    # Prevent metadata from escaping plugins/
    safe_name = Path(name).name

    return (
        jar_path.parent
        / safe_name
    )


def plugin_info(
    path: Path,
) -> dict:

    disabled = (
        path.name.endswith(
            ".jar.disabled"
        )
    )

    metadata = read_plugin_yml(
        path
    )

    filename = path.name

    if disabled:
        display_filename = (
            filename[:-9]
        )
    else:
        display_filename = filename


    name = metadata.get("name")

    if not name:
        name = re.sub(
            r"[-_ ]v?\d.*$",
            "",
            display_filename[:-4],
        )


    config_dir = (
        plugin_config_directory(
            path
        )
    )

    config_files = []
    if config_dir and config_dir.is_dir():
        plugin_root = path.parent.resolve()
        for config_file in config_dir.rglob("*"):
            if not config_file.is_file() or config_file.suffix.lower() not in {".yml", ".yaml"}:
                continue
            try:
                resolved = config_file.resolve()
                resolved.relative_to(config_dir.resolve())
                relative = resolved.relative_to(plugin_root.parent)
            except ValueError:
                continue
            config_files.append(relative.as_posix())


    return {
        "filename": filename,

        "name":
            name
            or display_filename,

        "version":
            metadata.get(
                "version"
            ),

        "enabled":
            not disabled,

        "size":
            path.stat().st_size,

        "config_directory":
            (
                config_dir.name
                if (
                    config_dir
                    and config_dir.is_dir()
                )
                else None
            ),

        "config_files": sorted(config_files, key=str.lower),
    }


def geyser_status(server, plugins: list[dict] | None = None) -> dict:
    plugins = plugins if plugins is not None else list_plugins(server)
    geyser = next((plugin for plugin in plugins if "geyser" in plugin["name"].casefold()), None)
    if not geyser:
        return {"installed": False, "enabled": False, "port": None}

    port = None
    config_directory = geyser.get("config_directory")
    if config_directory:
        config = plugins_directory(server) / config_directory / "config.yml"
        try:
            in_bedrock = False
            for raw_line in config.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                indent = len(raw_line) - len(raw_line.lstrip())
                if indent == 0:
                    in_bedrock = stripped == "bedrock:"
                    continue
                if in_bedrock:
                    match = re.fullmatch(r"port:\s*(\d+)", stripped)
                    if match:
                        candidate = int(match.group(1))
                        if 1 <= candidate <= 65535:
                            port = candidate
                        break
        except OSError:
            pass

    return {"installed": True, "enabled": bool(geyser["enabled"]), "port": port}


def list_plugins(server) -> list[dict]:

    directory = plugins_directory(
        server
    )

    if not directory.exists():
        return []

    plugins = []

    for path in directory.iterdir():

        if not path.is_file():
            continue

        if not (
            path.name.endswith(".jar")
            or path.name.endswith(
                ".jar.disabled"
            )
        ):
            continue

        plugins.append(
            plugin_info(path)
        )


    return sorted(
        plugins,
        key=lambda plugin:
            plugin["name"].lower(),
    )


def validate_plugin_archive(path: Path) -> None:
    if path.stat().st_size > MAX_PLUGIN_BYTES:
        raise ValueError("Plugin exceeds the configured size limit")
    try:
        with zipfile.ZipFile(path) as archive:
            if "plugin.yml" not in archive.namelist() and "paper-plugin.yml" not in archive.namelist():
                raise ValueError("JAR does not contain plugin.yml or paper-plugin.yml")
    except zipfile.BadZipFile as error:
        raise ValueError("Plugin is not a valid JAR archive") from error


def install_plugin_file(server, source: Path, filename: str) -> dict:
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.lower().endswith(".jar"):
        raise ValueError("Plugin filename must be a local .jar filename")
    validate_plugin_archive(source)
    directory = plugins_directory(server)
    directory.mkdir(parents=True, exist_ok=True)
    destination = safe_plugin_path(server, safe_name)
    if destination.exists() or destination.with_name(destination.name + ".disabled").exists():
        raise FileExistsError("Plugin already exists")
    temporary = directory / f".{safe_name}.upload"
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return plugin_info(destination)


def _validate_public_https_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Plugin URL must be a public HTTPS URL")
    if parsed.port not in {None, 443}:
        raise ValueError("Plugin URL must use the standard HTTPS port")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError("Plugin host could not be resolved") from error
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Plugin URL may not resolve to a private network")
    return parsed


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        _validate_public_https_url(new_url)
        return super().redirect_request(request, fp, code, message, headers, new_url)


def install_plugin_url(server, url: str) -> dict:
    parsed = _validate_public_https_url(url)
    filename = Path(urllib.parse.unquote(parsed.path)).name
    if not filename.lower().endswith(".jar"):
        raise ValueError("Plugin URL path must end in .jar")
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    request = urllib.request.Request(url, headers={"User-Agent": "STEMCraft-Console"})
    with tempfile.NamedTemporaryFile(prefix="stemcraft-plugin-", suffix=".jar") as temporary:
        with opener.open(request, timeout=120) as response:
            final = _validate_public_https_url(response.geturl())
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_PLUGIN_BYTES:
                raise ValueError("Plugin exceeds the configured size limit")
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_PLUGIN_BYTES:
                    raise ValueError("Plugin exceeds the configured size limit")
                temporary.write(chunk)
        final_name = Path(urllib.parse.unquote(final.path)).name
        if final_name.lower().endswith(".jar"):
            filename = final_name
        temporary.flush()
        return install_plugin_file(server, Path(temporary.name), filename)


def safe_plugin_path(
    server,
    filename: str,
) -> Path:

    directory = (
        plugins_directory(server)
        .resolve()
    )

    path = (
        directory
        / Path(filename).name
    ).resolve()

    if path.parent != directory:
        raise ValueError(
            "Invalid plugin path"
        )

    if not (
        path.name.endswith(".jar")
        or path.name.endswith(
            ".jar.disabled"
        )
    ):
        raise ValueError(
            "Invalid plugin file"
        )

    return path


def disable_plugin(
    server,
    filename: str,
):

    path = safe_plugin_path(
        server,
        filename,
    )

    if not path.exists():
        raise FileNotFoundError(
            "Plugin not found"
        )

    if path.name.endswith(
        ".jar.disabled"
    ):
        return

    destination = path.with_name(
        path.name + ".disabled"
    )

    if destination.exists():
        raise FileExistsError(
            "Disabled plugin already exists"
        )

    path.rename(destination)


def enable_plugin(
    server,
    filename: str,
):

    path = safe_plugin_path(
        server,
        filename,
    )

    if not path.exists():
        raise FileNotFoundError(
            "Plugin not found"
        )

    if not path.name.endswith(
        ".jar.disabled"
    ):
        return

    destination = path.with_name(
        path.name[:-9]
    )

    if destination.exists():
        raise FileExistsError(
            "Enabled plugin already exists"
        )

    path.rename(destination)


def remove_plugin(
    server,
    filename: str,
    remove_config: bool = False,
):

    path = safe_plugin_path(
        server,
        filename,
    )

    if not path.exists():
        raise FileNotFoundError(
            "Plugin not found"
        )


    config_dir = None

    if remove_config:
        config_dir = (
            plugin_config_directory(
                path
            )
        )


    path.unlink()


    if (
        config_dir
        and config_dir.exists()
        and config_dir.is_dir()
    ):
        import shutil

        shutil.rmtree(
            config_dir
        )
