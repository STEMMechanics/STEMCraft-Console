"""Structured metadata providers. Plugin projects are always administrator-configured."""
from dataclasses import asdict, dataclass
import json
import re
from urllib.parse import quote

import httpx

from ..paper import PAPER_API, USER_AGENT
from .versions import parse_version, compare_versions


@dataclass
class Release:
    version: str
    url: str
    date: str | None = None
    minecraft_versions: list[str] | None = None
    build: int | None = None
    checksums: dict | None = None
    download_url: str | None = None

    def to_dict(self):
        return asdict(self)


def text(value):
    if not isinstance(value, str) or not value or len(value) > 200 or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid release metadata')
    return value


def get_json(url):
    # All callers construct URLs from fixed mappings; never follow upstream links.
    with httpx.Client(timeout=15, follow_redirects=False, headers={'User-Agent': USER_AGENT}) as client:
        with client.stream('GET', url) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > 8 * 1024 * 1024:
                    raise ValueError('Release metadata exceeds size limit')
    return json.loads(data)


class Provider:
    name = ''
    def __init__(self, project):
        self.project = project

    @property
    def key(self):
        return f'{self.name}:{self.project}'

    def fetch(self):
        raise NotImplementedError

    def compare(self, installed, release, filename=None):
        return compare_versions(installed, release.version)

    def display_version(self, release):
        return release.version


class GitHub(Provider):
    name = 'GitHub Releases'

    @property
    def key(self):
        # GitHub repository names are case-insensitive; share caches between configurations.
        return f'{self.name}:{self.project.lower()}'

    def fetch(self):
        data = get_json(f'https://api.github.com/repos/{self.project}/releases/latest')
        if data.get('draft') or data.get('prerelease'):
            raise ValueError('No stable release')
        version = text(data['tag_name'])
        assets = [a for a in data.get('assets', []) if str(a.get('name', '')).endswith('.jar')]
        download = (f'https://github.com/{self.project}/releases/download/{quote(version, safe="")}/{quote(text(assets[0]["name"]), safe="")}'
                    if len(assets) == 1 else None)
        return [Release(version, f'https://github.com/{self.project}/releases/tag/{quote(version, safe="")}',
                        data.get('published_at'), download_url=download)]


class Modrinth(Provider):
    name = 'Modrinth'

    def release_version(self, value):
        return text(value)

    def fetch(self):
        data = get_json(f'https://api.modrinth.com/v2/project/{self.project}/version')
        releases = []
        if not isinstance(data, list):
            raise ValueError('Invalid release list')
        for item in data:
            if not isinstance(item.get('loaders'), list) or not isinstance(item.get('game_versions'), list):
                raise ValueError('Invalid compatibility metadata')
            if item.get('version_type') != 'release' or not set(item.get('loaders', [])) & {'paper', 'spigot', 'bukkit', 'purpur'}:
                continue
            versions = [text(v) for v in item['game_versions']]
            files = [f for f in item.get('files', []) if f.get('primary') and str(f.get('filename', '')).endswith('.jar')]
            download = None
            if len(files) == 1:
                from .http_source import validate_url
                from urllib.parse import urlsplit
                candidate = validate_url(files[0]['url'])
                if urlsplit(candidate).hostname == 'cdn.modrinth.com':
                    download = candidate
            releases.append(Release(self.release_version(item['version_number']),
                f'https://modrinth.com/plugin/{self.project}/version/{quote(text(item["id"]), safe="")}',
                item.get('date_published'), versions or None, download_url=download))
        return releases


class Paper(Provider):
    name = 'PaperMC'

    def fetch(self):
        if not re.fullmatch(r'[0-9A-Za-z._+-]+', self.project):
            raise ValueError('Invalid Minecraft version')
        builds = get_json(f'{PAPER_API}/projects/paper/versions/{self.project}/builds')
        checksums = {}
        for item in builds:
            for download in item.get('downloads', {}).values():
                sha = download.get('checksums', {}).get('sha256')
                if sha:
                    checksums[str(sha).lower()] = str(int(item['id']))
        releases = [Release(str(int(item['id'])), 'https://papermc.io/downloads/paper',
                            item.get('time'), [self.project])
                    for item in builds if str(item.get('channel', '')).upper() in {'STABLE', 'RECOMMENDED'}]
        if releases:
            # Share the checksum index once, rather than duplicating it for every build.
            releases[0].checksums = checksums
        return releases


def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).casefold())


def select_release(releases, minecraft_version):
    candidates = [r for r in releases if not r.minecraft_versions or not minecraft_version or minecraft_version in r.minecraft_versions]
    pool = candidates or releases
    if not pool:
        raise ValueError('No published releases for this platform')
    # Providers return stable releases except documented continuous CI providers.
    return max(pool, key=lambda r: parse_version(r.version) or parse_version('0'))
