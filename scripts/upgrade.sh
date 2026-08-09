#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck disable=SC1091
source "$SOURCE_DIR/scripts/common.sh"
banner "STEMCraft Console Upgrade"

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this upgrade as root." >&2
  exit 1
fi

INSTALL_DIR=/opt/stemcraft-console
BACKUP_DIR=/var/lib/stemcraft-console/upgrades/$(date -u +%Y%m%dT%H%M%SZ)

for required in app migrations alembic.ini requirements.txt deploy/stemcraft-console.service deploy/stemcraft-server@.service deploy/50-stemcraft-console.rules deploy/stemcraft-console; do
  [[ -e "$SOURCE_DIR/$required" ]] || {
    echo "Upgrade source is incomplete: missing $required" >&2
    exit 1
  }
done

MIGRATION_FILE=$(find "$SOURCE_DIR/migrations/versions" -maxdepth 1 -type f -name '*.py' -print -quit 2>/dev/null || true)
if [[ -z "$MIGRATION_FILE" ]]; then
  echo "Upgrade source is incomplete: no database migrations were found." >&2
  exit 1
fi
[[ -x "$INSTALL_DIR/.venv/bin/python" ]] || {
  echo "STEMCraft Console is not installed in $INSTALL_DIR." >&2
  exit 1
}

section "Creating rollback snapshot"
install -d -o stemcraft -g stemcraft "$BACKUP_DIR"
cp -a "$INSTALL_DIR/app" "$INSTALL_DIR/migrations" "$INSTALL_DIR/alembic.ini" "$INSTALL_DIR/requirements.txt" "$BACKUP_DIR/"
cp -a /var/lib/stemcraft-console/stemcraft-console.db "$BACKUP_DIR/" 2>/dev/null || true
section "Installing application update"
systemctl stop stemcraft-console.service
rm -rf "$INSTALL_DIR/app" "$INSTALL_DIR/migrations"
cp -R "$SOURCE_DIR/app" "$SOURCE_DIR/migrations" "$SOURCE_DIR/alembic.ini" "$SOURCE_DIR/requirements.txt" "$INSTALL_DIR/"
"$INSTALL_DIR/.venv/bin/python" -m pip install --requirement "$INSTALL_DIR/requirements.txt"
install -m 0644 "$SOURCE_DIR/deploy/stemcraft-console.service" /etc/systemd/system/stemcraft-console.service
install -m 0644 "$SOURCE_DIR/deploy/stemcraft-server@.service" /etc/systemd/system/stemcraft-server@.service
install -m 0644 "$SOURCE_DIR/deploy/50-stemcraft-console.rules" /etc/polkit-1/rules.d/50-stemcraft-console.rules
# Backfill the portable command location on installations made before this
# path was added. RHEL-family sudo secure_path values may omit /usr/local/sbin.
install -m 0755 "$SOURCE_DIR/deploy/stemcraft-console" /usr/bin/stemcraft-console
install -m 0755 "$SOURCE_DIR/deploy/stemcraft-console" /usr/local/sbin/stemcraft-console
chown -R stemcraft:stemcraft "$INSTALL_DIR"
systemctl daemon-reload
section "Starting STEMCraft Console"
systemctl start stemcraft-console.service

READY=false
CONFIG_FILE=/etc/stemcraft-console/console.env
WEB_HOST=$(sed -n 's/^STEMCRAFT_CONSOLE_HOST=//p' "$CONFIG_FILE" | tail -1)
WEB_PORT=$(sed -n 's/^STEMCRAFT_CONSOLE_PORT=//p' "$CONFIG_FILE" | tail -1)
WEB_HOST=${WEB_HOST:-127.0.0.1}
WEB_PORT=${WEB_PORT:-8000}
[[ "$WEB_HOST" == "0.0.0.0" ]] && WEB_HOST=127.0.0.1
[[ "$WEB_HOST" == "::" ]] && WEB_HOST=::1
if [[ "$WEB_HOST" == *:* ]]; then
  HEALTH_URL="http://[$WEB_HOST]:$WEB_PORT/health"
else
  HEALTH_URL="http://$WEB_HOST:$WEB_PORT/health"
fi
for _attempt in {1..30}; do
  if curl --fail --silent --globoff --noproxy '*' "$HEALTH_URL" >/dev/null; then
    READY=true
    break
  fi
  if ! systemctl is-active --quiet stemcraft-console.service; then
    break
  fi
  sleep 1
done
if [[ "$READY" != true ]]; then
  error "The upgraded service did not become healthy."
  echo "Roll back with: sudo $SOURCE_DIR/scripts/rollback.sh $BACKUP_DIR" >&2
  journalctl -u stemcraft-console.service --no-pager -n 30 >&2
  exit 1
fi

banner "STEMCraft Console upgrade complete"
info "Rollback files: $BACKUP_DIR"
