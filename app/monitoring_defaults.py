"""Read source defaults from application-root configuration, without network I/O."""
from functools import lru_cache
import logging
import os
from pathlib import Path

import yaml

from .update_providers import normalize_name

logger = logging.getLogger(__name__)
DEFAULTS_PATH = Path(__file__).resolve().parent.parent / 'plugin-monitoring.yml'
FIELDS = ('provider', 'project', 'version_pattern', 'link_pattern', 'installed_pattern')


def default_for(name):
    path = Path(os.getenv('STEMCRAFT_PLUGIN_MONITORING_DEFAULTS', str(DEFAULTS_PATH))).expanduser()
    try:
        stat = path.stat()
        entries, error = _load(str(path.resolve()), stat.st_mtime_ns, stat.st_size, stat.st_ino)
    except FileNotFoundError:
        return None, None
    except OSError:
        return None, 'Unable to read plugin monitoring defaults'
    entry = entries.get(normalize_name(name))
    return (dict(entry) if entry else None), error


@lru_cache(maxsize=8)
def _load(path, mtime, size, inode):
    # Stat signatures refresh edited/replaced files without restarting the Console.
    try:
        with open(path, 'rb') as source:
            raw = source.read(262145)
        if len(raw) > 262144:
            raise ValueError('Defaults file exceeds 256 KiB')
        data = yaml.safe_load(raw)
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('plugins'), dict):
            raise ValueError('Expected version 1 and a plugins mapping')
    except (OSError, ValueError, yaml.YAMLError, RecursionError):
        logger.warning('Unable to load plugin monitoring defaults; check the file format and access')
        return {}, 'Plugin monitoring defaults could not be loaded'
    from .plugin_monitoring import custom_provider
    entries = {}
    for name, definition in data['plugins'].items():
        if not isinstance(name, str) or not normalize_name(name):
            logger.warning('Ignoring a default monitoring entry with an invalid plugin name')
            continue
        names = [name]
        entry = {}
        try:
            if not isinstance(definition, dict):
                raise ValueError()
            aliases = definition.get('aliases', [])
            if not isinstance(aliases, list) or not all(isinstance(alias, str) and normalize_name(alias) for alias in aliases):
                raise ValueError()
            names += aliases
            entry = {field: definition.get(field, '') for field in FIELDS}
            provider = custom_provider(entry['provider'], entry['project'], entry['version_pattern'], entry['link_pattern'], entry['installed_pattern'])
            entry['project'] = provider.project
            notes = definition.get('notes', '')
            if not isinstance(notes, str) or len(notes) > 1000:
                raise ValueError()
            entry['notes'] = notes
        except (ValueError, TypeError):
            entry = {'error': 'Invalid default monitoring source; check plugin-monitoring.yml'}
            logger.warning('Invalid plugin monitoring default entry (source details omitted)')
        for alias in names:
            key = normalize_name(alias)
            if key in entries:
                entries[key] = {'error': 'Ambiguous plugin name/alias in monitoring defaults'}
                logger.warning('Duplicate plugin name/alias in monitoring defaults')
            else:
                entries[key] = entry
    return entries, None
