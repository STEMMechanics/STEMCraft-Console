"""Conservative ordering for plugin versions; opaque suffixes are not guessed."""
import re
from packaging.version import Version, InvalidVersion


def parse_version(value):
    value = str(value or '').strip().removeprefix('v').removeprefix('V')
    value = re.sub(r'(?i)-SNAPSHOT\s*\(build\s+(\d+)\)$', r'.dev\1', value)
    # Citizens, Vault and FAWE embed CI build numbers in their versions.
    value = re.sub(r'(?i)[ -]*(?:\(build\s+|build[ .-]*|b)(\d+)\)?$', r'.post\1', value)
    value = re.sub(r'(?i)-SNAPSHOT', '.dev0', value)
    try:
        return Version(value)
    except InvalidVersion:
        return None


def compare_versions(installed, latest):
    left, right = parse_version(installed), parse_version(latest)
    if left is None or right is None:
        return None
    # Local hashes are identities, not meaningful release ordering.
    left, right = Version(left.public), Version(right.public)
    return (right > left) - (right < left)
