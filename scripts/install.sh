#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/install.sh [--skip-packages]

Installs STEMCraft Console on Ubuntu or Oracle Linux. By default the installer
uses apt or dnf to install Python 3.10+, Java 21, polkit and supporting tools.

Options:
  --skip-packages  Do not install operating-system packages.
  -h, --help       Show this help.
EOF
}

SKIP_PACKAGES=false
INSTALL_ARGS=()
while (($#)); do
  case "$1" in
    --skip-packages)
      SKIP_PACKAGES=true
      INSTALL_ARGS+=(--skip-packages)
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this installer as root." >&2
  exit 1
fi

SOURCE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# When install.sh is piped directly to Bash it has no accompanying checkout.
# Fetch a temporary copy and hand the original arguments to that copy. When
# run from a checkout, continue directly with the local source instead.
if [[ ! -d "$SOURCE_DIR/app" || ! -f "$SOURCE_DIR/requirements.txt" ]]; then
  REPOSITORY=${STEMCRAFT_CONSOLE_REPOSITORY:-stemmechanics/stemcraft-console}
  REF=${STEMCRAFT_CONSOLE_REF:-main}

  for command in curl tar mktemp find; do
    command -v "$command" >/dev/null 2>&1 || {
      echo "Required bootstrap command not found: $command" >&2
      exit 1
    }
  done

  TEMP_DIR=$(mktemp -d /tmp/stemcraft-console-install.XXXXXX)
  cleanup() {
    rm -rf -- "$TEMP_DIR"
  }
  trap cleanup EXIT

  ARCHIVE="$TEMP_DIR/source.tar.gz"
  SOURCE_URL="https://github.com/$REPOSITORY/archive/refs/heads/$REF.tar.gz"
  echo "Downloading STEMCraft Console from $REPOSITORY ($REF)..."
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    "$SOURCE_URL" --output "$ARCHIVE"
  tar -xzf "$ARCHIVE" -C "$TEMP_DIR"

  REMOTE_INSTALLER=$(find "$TEMP_DIR" -mindepth 2 -maxdepth 3 -type f -path '*/scripts/install.sh' -print -quit)
  if [[ -z "$REMOTE_INSTALLER" ]]; then
    echo "The downloaded source does not contain scripts/install.sh." >&2
    exit 1
  fi

  chmod +x "$REMOTE_INSTALLER"
  "$REMOTE_INSTALLER" "${INSTALL_ARGS[@]}"
  exit $?
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Unable to identify this Linux distribution." >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
OS_ID=${ID,,}
OS_VERSION=${VERSION_ID%%.*}

case "$OS_ID" in
  ubuntu)
    if ((OS_VERSION < 22)); then
      echo "Ubuntu 22.04 or newer is required." >&2
      exit 1
    fi
    PACKAGE_MANAGER=apt
    PYTHON_BIN=python3
    PACKAGES=(python3 python3-venv python3-pip openjdk-21-jre-headless policykit-1 ca-certificates curl)
    ;;
  ol|oracle|oraclelinux)
    if ((OS_VERSION < 8)); then
      echo "Oracle Linux 8 or newer is required." >&2
      exit 1
    fi
    PACKAGE_MANAGER=dnf
    PYTHON_BIN=python3.11
    PACKAGES=(python3.11 python3.11-pip java-21-openjdk-headless polkit ca-certificates curl)
    ;;
  *)
    echo "Unsupported distribution '$OS_ID'. Supported: Ubuntu and Oracle Linux." >&2
    exit 1
    ;;
esac

if [[ "$SKIP_PACKAGES" == false ]]; then
  if [[ "$PACKAGE_MANAGER" == apt ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends "${PACKAGES[@]}"
  else
    dnf install -y "${PACKAGES[@]}"
  fi
fi

for command in "$PYTHON_BIN" systemctl useradd install cp; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Required command not found: $command" >&2
    exit 1
  }
done

PYTHON_VERSION=$(
  "$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
)
"$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' || {
  echo "Python 3.10 or newer is required; found $PYTHON_VERSION." >&2
  exit 1
}

INSTALL_DIR=/opt/stemcraft-console
DATA_DIR=/var/lib/stemcraft-console
SERVER_DIR=/srv/minecraft
CONFIG_DIR=/etc/stemcraft-console
SERVICE_USER=stemcraft
SERVICE_GROUP=stemcraft

for required in app migrations alembic.ini requirements.txt deploy/stemcraft-console.service deploy/stemcraft-server@.service deploy/50-stemcraft-console.rules deploy/stemcraft-console; do
  [[ -e "$SOURCE_DIR/$required" ]] || {
    echo "Installation source is incomplete: missing $required" >&2
    exit 1
  }
done

if [[ -e "$INSTALL_DIR/app" ]]; then
  echo "STEMCraft Console is already installed. Use scripts/upgrade.sh." >&2
  exit 1
fi

NOLOGIN_SHELL=$(command -v nologin || true)
NOLOGIN_SHELL=${NOLOGIN_SHELL:-/sbin/nologin}
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  if getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
    useradd --system --home-dir "$DATA_DIR" --shell "$NOLOGIN_SHELL" --gid "$SERVICE_GROUP" "$SERVICE_USER"
  else
    useradd --system --home-dir "$DATA_DIR" --shell "$NOLOGIN_SHELL" --user-group "$SERVICE_USER"
  fi
fi
if getent group systemd-journal >/dev/null 2>&1; then
  usermod -a -G systemd-journal "$SERVICE_USER"
fi

install -d -m 0755 -o root -g root "$INSTALL_DIR"
install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_GROUP" "$DATA_DIR" "$DATA_DIR/upgrades" "$SERVER_DIR"
install -d -m 0750 -o root -g "$SERVICE_GROUP" "$CONFIG_DIR"
cp -a "$SOURCE_DIR/app" "$SOURCE_DIR/migrations" "$SOURCE_DIR/alembic.ini" "$SOURCE_DIR/requirements.txt" "$INSTALL_DIR/"

"$PYTHON_BIN" -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
"$INSTALL_DIR/.venv/bin/python" -m pip install --requirement "$INSTALL_DIR/requirements.txt"

INITIAL_ADMIN_PASSWORD=
if [[ ! -f "$CONFIG_DIR/console.env" ]]; then
  SECRET=$("$INSTALL_DIR/.venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(48))')
  INITIAL_ADMIN_PASSWORD=$("$INSTALL_DIR/.venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(18))')
  install -m 0640 -o root -g "$SERVICE_GROUP" /dev/null "$CONFIG_DIR/console.env"
  {
    echo "STEMCRAFT_CONSOLE_SECRET=$SECRET"
    echo "STEMCRAFT_CONSOLE_DATABASE=$DATA_DIR/stemcraft-console.db"
    echo "STEMCRAFT_CONSOLE_SERVER_ROOT=$SERVER_DIR"
    echo "STEMCRAFT_CONSOLE_HOST=127.0.0.1"
    echo "STEMCRAFT_CONSOLE_PORT=8000"
    echo "STEMCRAFT_CONSOLE_COOKIE_SECURE=true"
    echo "STEMCRAFT_CONSOLE_ADMIN_USER=admin"
    echo "STEMCRAFT_CONSOLE_ADMIN_PASSWORD=$INITIAL_ADMIN_PASSWORD"
  } > "$CONFIG_DIR/console.env"
fi

install -m 0644 "$SOURCE_DIR/deploy/stemcraft-console.service" /etc/systemd/system/stemcraft-console.service
install -m 0644 "$SOURCE_DIR/deploy/stemcraft-server@.service" /etc/systemd/system/stemcraft-server@.service
install -d -m 0755 /etc/polkit-1/rules.d
install -m 0644 "$SOURCE_DIR/deploy/50-stemcraft-console.rules" /etc/polkit-1/rules.d/50-stemcraft-console.rules
install -m 0755 "$SOURCE_DIR/deploy/stemcraft-console" /usr/local/sbin/stemcraft-console

chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR" "$SERVER_DIR"
systemctl daemon-reload
systemctl enable --now stemcraft-console.service

READY=false
for _attempt in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8000/health >/dev/null; then
    READY=true
    break
  fi
  if ! systemctl is-active --quiet stemcraft-console.service; then
    break
  fi
  sleep 1
done

if [[ "$READY" != true ]]; then
  echo "The service did not start. Recent logs:" >&2
  journalctl -u stemcraft-console.service --no-pager -n 30 >&2
  exit 1
fi

cat <<'EOF'
STEMCraft Console is running at http://127.0.0.1:8000.

Next steps:
  1. Configure an HTTPS reverse proxy.
  2. Sign in and change the generated administrator password.
  3. Use 'sudo stemcraft-console status' to inspect the service.
EOF

if [[ -n "$INITIAL_ADMIN_PASSWORD" ]]; then
  printf '\nInitial administrator: admin\nInitial password: %s\n' "$INITIAL_ADMIN_PASSWORD"
  echo "The password is stored in $CONFIG_DIR/console.env until you remove that line."
fi
