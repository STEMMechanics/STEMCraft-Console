<div align="center">

# STEMCraft Console

**Web-based management console for STEMCraft Minecraft servers.**

[STEMCraft](https://www.stemmechanics.com.au/stemcraft) | [STEMMechanics](https://www.stemmechanics.com.au/)

</div>

---

<!-- Replace with an actual screenshot once added to the repository.

<div align="center">
  <img alt="STEMCraft Console Overview" src="docs/images/overview.png" />
</div>

---

-->

STEMCraft Console is the server management interface developed for **STEMCraft**, a Minecraft community operated by **STEMMechanics**.

It provides a straightforward web interface for managing STEMCraft's Minecraft servers without requiring administrators to work directly from the command line.

STEMCraft Console is designed primarily around **Minecraft Java Edition running PaperMC**. It may work with other Paper-compatible servers, but PaperMC is the platform we develop and test against.

---

## Quick Start

For a production Linux host, use the installer below. For local development,
use the development installation steps.

### Production installation

The installer creates a locked-down `stemcraft` service account, an application
virtual environment, systemd services, a persistent secret, and data directories.
It supports the following systemd-based distributions:

| Distribution | Supported versions | Package manager |
| --- | --- | --- |
| Ubuntu | 22.04 and newer | `apt` |
| Oracle Linux | 8 and newer | `dnf` |

For a one-line installation from the official GitHub repository:

```bash
curl -fsSL https://dev.stemcraft.com.au/install.sh | sudo bash
```

This redirects to the installer in the official GitHub repository, resolves
the latest published release, downloads that tagged source into a temporary
directory, and runs the same installer described below. It does not install
unreleased commits from `main`. Review the [installer script](scripts/install.sh)
before piping it to a shell. For a reviewable or version-controlled installation,
clone a trusted release checkout and run:

```bash
sudo ./scripts/install.sh
```

The installer installs Python, polkit and supporting system packages. It
detects and preserves existing Java installations without adding or replacing
older runtimes. Interactive installs ask which Java versions to add, and a
blank response installs none. Automated installs add no Java by default; repeat
`--java-version` to select one or more runtimes, for example
`--java-version 21 --java-version 25`.
Paper 26.1 and newer require Java 25, while older servers can retain their
compatible runtime. Each server's Java executable can be selected during
creation or from its Properties page, and the System page lists all detected
runtimes.
During the first startup after upgrading, legacy servers that did not have an
explicit Java selection are assigned the installed runtime recommended for
their recorded Minecraft version. Existing explicit selections are preserved.
Use `--skip-packages` only when those dependencies have already been installed.
It does not configure a firewall or reverse proxy.

On a fresh interactive installation, it asks for the IP address and port the
web service should bind to. Press Enter to keep `0.0.0.0:8000`, which listens on
all network interfaces. For unattended
installation, provide explicit values or accept the defaults:

```bash
sudo ./scripts/install.sh --host 0.0.0.0 --port 8000 --non-interactive
```

Use `--host 127.0.0.1` when the panel should only be reachable through a local
reverse proxy. Repair installations retain the address already saved in
`/etc/stemcraft-console/console.env`; pass `--host 0.0.0.0` explicitly to
change an existing loopback-only installation.

On a fresh installation it prints a generated password for the initial `admin`
account exactly once. Only its one-way hash is stored in the database; the
plaintext password is not written to `console.env`. The account must change the
temporary password after signing in.

The initial configuration permits its session cookie over HTTP until a reverse
proxy is configured. Once HTTPS is
working, set the following in `/etc/stemcraft-console/console.env` and restart
the service:

```text
STEMCRAFT_CONSOLE_COOKIE_SECURE=true
```

The installer is safe to run again if the first service start fails. It keeps
the database, configuration, Minecraft servers, and generated login details
while repairing the application and systemd files:

```bash
curl -fsSL https://dev.stemcraft.com.au/install.sh | sudo bash
```

For startup diagnostics, use:

```bash
sudo journalctl -u stemcraft-console.service --no-pager -n 200
```

The panel binds to the address and port selected during installation. Configure
an HTTPS reverse proxy before exposing it. Persistent files are stored in these
locations:

| Path | Purpose |
| --- | --- |
| `/opt/stemcraft-console` | Application and Python virtual environment |
| `/etc/stemcraft-console/console.env` | Service configuration and session secret |
| `/var/lib/stemcraft-console` | Database and upgrade snapshots |
| `/srv/minecraft` | Managed Minecraft instances and backups |

Useful service commands are available through the installed helper:

```bash
stemcraft-console status
stemcraft-console restart
stemcraft-console logs
stemcraft-console reset-password admin
stemcraft-console server survival restart
stemcraft-console server survival logs
```

Privileged actions automatically rerun through `sudo` using the helper's
resolved absolute path. The helper is installed at `/usr/bin/stemcraft-console` so it remains
available when `sudo` uses a restricted `secure_path`, including the default on
Oracle Linux 8. Upgrading or rerunning the installer in repair mode adds this
path to existing installations that only have the legacy
`/usr/local/sbin/stemcraft-console` copy.

The in-panel application updater cannot modify root-owned command locations.
After updating an older installation that lacks `/usr/bin/stemcraft-console`,
repair it once with the release installer. Until then, use the legacy absolute
path:

```bash
sudo /usr/local/sbin/stemcraft-console restart
curl -fsSL https://dev.stemcraft.com.au/install.sh | sudo bash
```

The final example uses the server's systemd service name, which is configured
when the server is created or imported in the panel.

### Importing existing servers

Administrators can use **Import Server** to discover unmanaged Minecraft
directories under the configured server root or inspect an absolute path such
as `/opt/minecraft`. Before enabling import, the panel checks:

- `server.properties`, the selected server JAR, port, and EULA state;
- effective directory and file access for the account running the panel;
- an actual temporary write when the import is submitted;
- existing systemd units associated with the directory; and
- whether the configured Minecraft port is already occupied.

An active or enabled external service must be stopped and disabled before
STEMCraft Console adopts the directory. This avoids two services writing the
same world or attempting to bind the same port. Production imports cannot use
home directories because the installed services retain `ProtectHome=true`.

Importing a path outside `/srv/minecraft` requires rerunning the installer from
the release that added external-path imports. That refreshes the systemd
sandbox policy; normal Unix ownership and permissions still apply.

To upgrade from a newer trusted release checkout:

```bash
sudo ./scripts/upgrade.sh
```

Each upgrade saves the previous application and database under
`/var/lib/stemcraft-console/upgrades/TIMESTAMP`. To roll back, pass that exact
directory to:

```bash
sudo ./scripts/rollback.sh /var/lib/stemcraft-console/upgrades/TIMESTAMP
```

### Publishing a release

Set `APP_VERSION` in `app/version.py`, merge the release-preparation PR, then
tag that exact commit. For version 0.2.3:

```bash
git switch main
git pull --ff-only
git tag 0.2.3
git push origin 0.2.3
```

The release workflow verifies that the tag matches `APP_VERSION`, creates the
GitHub release, and attaches a versioned application archive with its SHA-256
checksum. Both `0.2.3` and `v0.2.3` tag styles are supported, but the existing
unprefixed style is preferred for consistency. The one-line installer resolves
GitHub's latest published release and will begin installing it once the release
has been published.

To uninstall the application while preserving the database, configuration,
upgrade snapshots, backups, and Minecraft servers:

```bash
sudo ./scripts/uninstall.sh --confirm
```

For a completely clean uninstall, including the database, configuration,
backups, upgrade snapshots, service account, and every Minecraft server:

```bash
sudo ./scripts/uninstall.sh --purge-all --confirm
```

> **Warning:** `--purge-all` permanently deletes every managed Minecraft world
> and server file under `/srv/minecraft`. It cannot be undone unless you have a
> separate backup.

### Development installation

Clone the repository:

```bash
git clone https://github.com/stemmechanics/stemcraft-console.git
cd stemcraft-console
```

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply the database migrations:

```bash
alembic upgrade head
```

Create the first local administrator and save the temporary password shown:

```bash
python -m app.admin_cli ensure-admin --username admin
```

Start STEMCraft Console:

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

The bundled CodeMirror editor is committed under `app/static` so production
installations do not require Node.js. When changing `editor-source.js`, rebuild
that asset with:

```bash
npm install
npm run build:editor
```

Set a persistent, randomly generated secret before first use (at least 32
characters). Without one, the development server generates a temporary secret
and sessions are invalidated on restart:

```bash
export STEMCRAFT_CONSOLE_SECRET="replace-with-a-long-random-value"
```

For HTTPS deployments, also set
`STEMCRAFT_CONSOLE_COOKIE_SECURE=true`. File uploads default to a 512 MiB limit;
override it with `STEMCRAFT_CONSOLE_MAX_UPLOAD_BYTES` when required.

---

## Requirements

|             | Requirement                                                        |
| ----------- | ------------------------------------------------------------------ |
| Minecraft   | Java Edition                                                       |
| Server      | PaperMC                                                            |
| OS          | Ubuntu 22.04+ or Oracle Linux 8+ for production                     |
| Python      | Python 3.10 or newer                                                |
| Database    | SQLite                                                             |
| Java        | Java 21 by default; the managed Minecraft version must support it   |
| Off-site backups | rclone (optional)                                           |
| Development | macOS is supported locally; Windows is not currently supported     |

> PaperMC is the primary server platform targeted by STEMCraft Console. Other Paper-compatible or Bukkit-derived implementations may work but are not currently tested or officially supported.

---

## Server Management

STEMCraft Console manages multiple Minecraft servers from a single interface.

Each server has its own:

```text
Server directory
Minecraft version
PaperMC build
Initial and maximum Java memory allocation
Server JAR and JVM startup options
Network port
Plugins
Configuration
Files
Backups
User access
```

The console is intended to provide the common administration tools required to operate STEMCraft without requiring routine shell access to the server.

### Off-site Backups

Scheduled backups can copy the completed local ZIP to any configured
[rclone](https://rclone.org/) remote, including Backblaze B2, Storj, S3 and
SFTP. Install rclone on the console server, then add and test destinations from
**Settings → Off-site Backups**. The panel writes credentials to a private
service-owned configuration file; saved secrets are not returned to the browser.
An explicit configuration location remains available for advanced deployments:

```env
STEMCRAFT_RCLONE_CONFIG=/etc/stemcraft-console/rclone.conf
```

Use Settings to test a bucket or directory. A backup schedule accepts a destination such as
`b2:bucket/minecraft-backups` and maintains independent local and off-site
retention counts. Local backup success is preserved if an upload fails; the run
is shown with a warning so it can be retried or investigated.

### Server Processes

During development, Minecraft servers may be launched directly by STEMCraft Console.

Production deployments are intended to use independent **systemd services** for Minecraft instances.

This allows Minecraft servers to continue running when STEMCraft Console is stopped, restarted or upgraded.
Choose the systemd process backend while creating a server. The installer grants
the panel service permission to manage only `stemcraft-server@*.service` units;
server names, JAR filenames, memory values, and JVM arguments are validated and
passed without a shell.

For a systemd-backed server, **Start**, **Stop**, and **Restart** control the
current runtime without changing whether the instance starts after a host
reboot. Use **Start automatically at boot** in server Properties to enable or
disable that systemd boot policy independently.

The installed units are:

- `stemcraft-console.service` for the web panel and scheduled work.
- `stemcraft-server@.service` for independently managed Minecraft instances.

Use `journalctl -u stemcraft-console.service` for panel logs or
`journalctl -u stemcraft-server@NAME.service` for a Minecraft instance. The
`stemcraft-console` command shown above provides shorter equivalents.

---

## Database & Upgrades

STEMCraft Console uses **SQLite** for application data and **Alembic** for database schema migrations.

After updating the application, apply outstanding migrations with:

```bash
alembic upgrade head
```

The application also applies pending migrations automatically during startup.
Running the command manually remains useful for deployments that migrate before
restarting the service.

Administrators can check for releases, install or roll back an update, and
restart the console from the Application Version row in System Settings. A
server-wide maintenance lock prevents connected users from making changes
during these operations. The panel waits for systemd to bring the service back
and then reloads every connected client, so routine upgrades do not require an
SSH session.

Developers making model changes can generate a migration with:

```bash
alembic revision --autogenerate -m "Description of change"
```

Review the generated migration before applying it:

```bash
alembic upgrade head
```

Database migrations are designed to allow existing installations to upgrade without deleting or recreating their database.

---

## Authentication & Security

STEMCraft Console requires authenticated user accounts and supports:

- Single-role user assignments without role inheritance
- Fine-grained permissions for servers, console, players, plugins, files,
  backups, automation, users, roles, system controls, and global settings
- An immutable Administrator role with full access
- Per-server access permissions for roles without global server access
- Password hashing
- Forced password changes
- TOTP two-factor authentication
- Recovery codes
- Email-based password recovery
- SMTP configuration

The management interface provides access to Minecraft console commands, server files and configuration. It should therefore be treated as an administrative interface.

Production installations should use HTTPS and should not expose the console to untrusted networks without appropriate security controls.

The authenticated interface supports desktop, tablet, and mobile viewport
sizes. Navigation, forms, tables, dialogs, notifications, and server-management
controls adapt at responsive breakpoints without requiring a separate mobile
application.

### Reporting a Vulnerability

Please **do not create a public GitHub issue** for security vulnerabilities.

Instead:

- [Report a vulnerability privately through GitHub](https://github.com/stemmechanics/stemcraft-console/security/advisories/new)
- [Email STEMMechanics](mailto:hello@stemmechanics.com.au)

See our [Security Policy](SECURITY.md) for further information.

---

## Project Status

STEMCraft Console is under active development.

It is developed primarily to support **STEMCraft**, so development priorities are driven by the requirements of the STEMCraft community and STEMMechanics workshops rather than the goal of creating a universal Minecraft hosting platform.

The project is open source, and others running PaperMC servers are welcome to use, adapt and contribute to it.

Expect interfaces, configuration and installation procedures to change while the project approaches its first stable release.

---

## Contributing

Bug reports, improvements and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

For larger changes, please open an issue first.

Run the test suite with:

```bash
pytest
```

|     |                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------- |
| 🐛   | [Report a Bug](https://github.com/stemmechanics/stemcraft-console/issues/new?template=bug_report.yml)            |
| ✨   | [Request a Feature](https://github.com/stemmechanics/stemcraft-console/issues/new?template=feature_request.yml)  |
| 💡   | [Suggest an Improvement](https://github.com/stemmechanics/stemcraft-console/issues/new?template=improvement.yml) |
| 🔧   | [Propose a Refactor](https://github.com/stemmechanics/stemcraft-console/issues/new?template=refactor.yml)        |

[View all issue options](https://github.com/stemmechanics/stemcraft-console/issues/new/choose)

---

## Acknowledgements

The interface and user experience of STEMCraft Console were inspired in part by [Fabricator](https://github.com/philderks/Fabricator), an open-source Minecraft server management panel created by Phil Derks.

STEMCraft Console is an independent implementation and does not contain Fabricator source code or assets.

STEMCraft Console is built primarily for [PaperMC](https://papermc.io/).

Minecraft is a trademark of Microsoft Corporation. STEMCraft Console and STEMMechanics are not affiliated with or endorsed by Mojang Studios or Microsoft.

---

## About STEMMechanics

STEMCraft Console is a project of [STEMMechanics](https://www.stemmechanics.com.au/).

STEMMechanics develops and delivers hands-on STEM, coding, engineering and creative technology experiences for young people and communities.

[STEMCraft](https://www.stemmechanics.com.au/stemcraft) extends that work into Minecraft, providing a managed online environment for collaborative building, challenges, workshops and community activities.

---

## License

[GPL-3.0-or-later](LICENSE)

STEMCraft Console is free and open-source software licensed under the GNU General Public License version 3 or any later version.

Copyright © 2026 STEMMechanics
