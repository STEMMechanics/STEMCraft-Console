import os
import tempfile
from pathlib import Path

from .file_manager import yaml_sanity_warning


MAX_YAML_BYTES = 1024 * 1024
ROOT_FILES = {
    "bukkit.yml": ("Bukkit and Spigot", "Bukkit"),
    "spigot.yml": ("Bukkit and Spigot", "Spigot"),
    "commands.yml": ("Bukkit and Spigot", "Commands"),
    "help.yml": ("Bukkit and Spigot", "Help"),
    "permissions.yml": ("Bukkit and Spigot", "Permissions"),
}
PAPER_FILES = {
    "config/paper-global.yml": ("Paper", "Global settings"),
    "config/paper-world-defaults.yml": ("Paper", "World defaults"),
}


def _safe_config_path(server, relative: str) -> Path:
    root = Path(server.directory).resolve()
    relative_path = Path(relative)
    normalized = relative_path.as_posix()
    is_world_override = (
        len(relative_path.parts) == 2
        and relative_path.name == "paper-world.yml"
        and relative_path.parts[0] not in {".", "..", "config", "plugins"}
    )
    if relative_path.is_absolute() or (normalized not in ROOT_FILES and normalized not in PAPER_FILES and not is_world_override):
        raise ValueError("Configuration file is not available")
    candidate = root / relative
    if candidate.is_symlink():
        raise ValueError("Configuration file cannot be a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        raise ValueError("Configuration file is not available") from None
    if not resolved.is_file() or resolved.suffix.lower() not in {".yml", ".yaml"}:
        raise ValueError("Configuration file is not available")
    return resolved


def discover_advanced_properties(server) -> list[dict]:
    root = Path(server.directory).resolve()
    grouped = {}
    known = {**ROOT_FILES, **PAPER_FILES}
    candidates = list(known)
    candidates.extend(
        str(path.relative_to(root))
        for path in root.glob("*/paper-world.yml")
        if path.is_file()
    )
    for relative in candidates:
        try:
            path = _safe_config_path(server, relative)
            if path.stat().st_size > MAX_YAML_BYTES:
                continue
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError):
            continue
        if relative in known:
            group, label = known[relative]
        else:
            group = "World overrides"
            label = f"{Path(relative).parent.name} world settings"
        grouped.setdefault(group, []).append({
            "path": relative,
            "label": label,
            "content": content,
        })
    order = ("Paper", "Bukkit and Spigot", "World overrides")
    return [
        {"name": name, "files": sorted(grouped[name], key=lambda item: item["label"].lower())}
        for name in order if grouped.get(name)
    ]


def save_advanced_property(server, relative: str, content: str):
    if len(content.encode("utf-8")) > MAX_YAML_BYTES:
        raise ValueError("YAML configuration cannot exceed 1 MiB")
    path = _safe_config_path(server, relative)
    warning = yaml_sanity_warning(content)

    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            if content and not content.endswith("\n"):
                handle.write("\n")
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return warning
