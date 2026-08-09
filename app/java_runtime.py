import re
import shutil
import subprocess
from pathlib import Path


JAVA_ROOTS = (Path("/usr/lib/jvm"), Path("/usr/java"), Path("/opt/java"))


def _java_details(path: Path) -> dict | None:
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            return None
        result = subprocess.run(
            [str(resolved), "-version"], capture_output=True, text=True,
            timeout=10, check=False,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None
    output = (result.stderr or result.stdout).strip()
    match = re.search(r'(?:java|openjdk) version "([^"]+)"', output, re.I)
    if not match:
        return None
    version = match.group(1)
    first = version.split(".", 1)[0]
    major = int(version.split(".")[1] if first == "1" else first)
    vendor_line = next((line.strip() for line in output.splitlines()[1:] if line.strip()), "Java")
    return {"path": str(resolved), "major": major, "version": version, "name": vendor_line}


def discover_java_runtimes() -> list[dict]:
    candidates = set()
    current = shutil.which("java")
    if current:
        candidates.add(Path(current))
    for root in JAVA_ROOTS:
        if root.is_dir():
            candidates.update(root.glob("*/bin/java"))
            candidates.update(root.glob("*/*/bin/java"))
    runtimes = {}
    for candidate in candidates:
        details = _java_details(candidate)
        if details:
            runtimes[details["path"]] = details
    return sorted(runtimes.values(), key=lambda item: (item["major"], item["path"]), reverse=True)


def resolve_java_path(value: str) -> str:
    requested = str(value or "java").strip()
    if requested == "java":
        requested = shutil.which("java") or ""
    try:
        resolved = str(Path(requested).resolve(strict=True))
    except (OSError, RuntimeError):
        raise ValueError("Select an installed Java runtime") from None
    if resolved not in {item["path"] for item in discover_java_runtimes()}:
        raise ValueError("Select an installed Java runtime")
    return resolved


def recommended_java_major(minecraft_version: str | None) -> int:
    if not minecraft_version:
        return 25
    parts = [int(value) for value in re.findall(r"\d+", minecraft_version)]
    if not parts:
        return 25
    if parts[0] >= 26:
        return 25
    version = tuple((parts + [0, 0])[:3])
    if version >= (1, 20, 0):
        return 21
    if version >= (1, 17, 0):
        return 17
    if version >= (1, 16, 5):
        return 16
    if version >= (1, 12, 0):
        return 11
    return 8


def select_java_runtime(runtimes: list[dict], minecraft_version: str | None) -> str | None:
    recommended = recommended_java_major(minecraft_version)
    exact = next((item for item in runtimes if item["major"] == recommended), None)
    return (exact or (runtimes[0] if runtimes else None) or {}).get("path")
