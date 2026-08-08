#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 || ${1:-} != "--confirm" ]]; then
  echo "Usage: sudo $0 --confirm" >&2
  echo "Application files are removed; server and database data are preserved." >&2
  exit 1
fi

INSTALL_DIR=/opt/stemcraft-console
CONFIG_DIR=/etc/stemcraft-console
DATA_DIR=/var/lib/stemcraft-console
SERVER_DIR=/srv/minecraft

echo "Stopping and disabling STEMCraft Console..."
systemctl disable --now stemcraft-console.service 2>/dev/null || true
rm -f /etc/systemd/system/stemcraft-console.service /etc/systemd/system/stemcraft-server@.service
rm -f /etc/polkit-1/rules.d/50-stemcraft-console.rules
rm -f /usr/local/sbin/stemcraft-console
systemctl daemon-reload

echo "Removing application files from $INSTALL_DIR..."
rm -rf -- "$INSTALL_DIR"

if [[ -e "$INSTALL_DIR" ]]; then
  echo "Uninstall failed: $INSTALL_DIR still exists." >&2
  echo "Check whether it is a read-only mount or has immutable files:" >&2
  echo "  findmnt $INSTALL_DIR" >&2
  echo "  lsattr -R $INSTALL_DIR" >&2
  exit 1
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
