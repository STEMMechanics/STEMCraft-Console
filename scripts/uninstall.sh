#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  sudo $0 --confirm
  sudo $0 --purge-all --confirm

Options:
  --confirm    Required confirmation for either uninstall mode.
  --purge-all Permanently remove the application, database, configuration,
              upgrade snapshots, backups, and every Minecraft server.

Without --purge-all, application files are removed while all data is preserved.
EOF
}

CONFIRMED=false
PURGE_ALL=false
while (($#)); do
  case "$1" in
    --confirm) CONFIRMED=true ;;
    --purge-all) PURGE_ALL=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this uninstaller as root." >&2
  usage >&2
  exit 1
fi

if [[ "$CONFIRMED" != true ]]; then
  echo "Uninstall confirmation is required." >&2
  usage >&2
  exit 1
fi

INSTALL_DIR=/opt/stemcraft-console
CONFIG_DIR=/etc/stemcraft-console
DATA_DIR=/var/lib/stemcraft-console
SERVER_DIR=/srv/minecraft
RUNTIME_DIR=/run/stemcraft-console
SERVICE_USER=stemcraft
SERVICE_GROUP=stemcraft

remove_tree() {
  local target=$1
  if ! rm -rf -- "$target"; then
    echo "Unable to remove $target." >&2
    return 1
  fi
  if [[ -e "$target" ]]; then
    echo "Uninstall failed: $target still exists." >&2
    echo "Check whether it is a read-only mount or has immutable files:" >&2
    echo "  findmnt $target" >&2
    echo "  lsattr -R $target" >&2
    return 1
  fi
}

echo "Stopping and disabling STEMCraft Console..."
systemctl disable --now stemcraft-console.service 2>/dev/null || true

if [[ "$PURGE_ALL" == true ]]; then
  echo "Stopping all managed Minecraft services..."
  systemctl disable --now 'stemcraft-server@*.service' 2>/dev/null || true
fi

rm -f /etc/systemd/system/stemcraft-console.service /etc/systemd/system/stemcraft-server@.service
rm -f /etc/polkit-1/rules.d/50-stemcraft-console.rules
rm -f /usr/local/sbin/stemcraft-console
systemctl daemon-reload

echo "Removing application files from $INSTALL_DIR..."
remove_tree "$INSTALL_DIR"

if [[ "$PURGE_ALL" == true ]]; then
  echo "Permanently removing all STEMCraft Console and Minecraft data..."
  remove_tree "$DATA_DIR"
  remove_tree "$SERVER_DIR"
  remove_tree "$CONFIG_DIR"
  remove_tree "$RUNTIME_DIR"

  if id "$SERVICE_USER" >/dev/null 2>&1; then
    userdel "$SERVICE_USER"
  fi
  if getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
    groupdel "$SERVICE_GROUP" 2>/dev/null || true
  fi

  cat <<EOF
STEMCraft Console was completely removed.

Deleted permanently:
  $INSTALL_DIR
  $DATA_DIR
  $SERVER_DIR
  $CONFIG_DIR
  $RUNTIME_DIR
  service account: $SERVICE_USER
EOF
  exit 0
fi

cat <<EOF
STEMCraft Console application files were removed successfully.

Preserved data:
  $DATA_DIR
  $SERVER_DIR
  $CONFIG_DIR

Running the installer again will reuse the preserved database, servers, and
administrator credentials. Remove those directories separately only if you
intend to permanently delete their contents.
EOF
