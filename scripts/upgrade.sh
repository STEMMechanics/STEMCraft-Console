#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this upgrade as root." >&2
  exit 1
fi

SOURCE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALL_DIR=/opt/stemcraft-console
BACKUP_DIR=/var/lib/stemcraft-console/upgrades/$(date -u +%Y%m%dT%H%M%SZ)

for required in app migrations alembic.ini requirements.txt deploy/stemcraft-console.service deploy/stemcraft-server@.service deploy/50-stemcraft-console.rules deploy/stemcraft-console; do
  [[ -e "$SOURCE_DIR/$required" ]] || {
    echo "Upgrade source is incomplete: missing $required" >&2
    exit 1
  }
done
[[ -x "$INSTALL_DIR/.venv/bin/python" ]] || {
  echo "STEMCraft Console is not installed in $INSTALL_DIR." >&2
  exit 1
}

install -d -o stemcraft -g stemcraft "$BACKUP_DIR"
cp -a "$INSTALL_DIR/app" "$INSTALL_DIR/migrations" "$INSTALL_DIR/alembic.ini" "$INSTALL_DIR/requirements.txt" "$BACKUP_DIR/"
cp -a /var/lib/stemcraft-console/stemcraft-console.db "$BACKUP_DIR/" 2>/dev/null || true
systemctl stop stemcraft-console.service
rm -rf "$INSTALL_DIR/app" "$INSTALL_DIR/migrations"
cp -R "$SOURCE_DIR/app" "$SOURCE_DIR/migrations" "$SOURCE_DIR/alembic.ini" "$SOURCE_DIR/requirements.txt" "$INSTALL_DIR/"
"$INSTALL_DIR/.venv/bin/python" -m pip install --requirement "$INSTALL_DIR/requirements.txt"
install -m 0644 "$SOURCE_DIR/deploy/stemcraft-console.service" /etc/systemd/system/stemcraft-console.service
install -m 0644 "$SOURCE_DIR/deploy/stemcraft-server@.service" /etc/systemd/system/stemcraft-server@.service
install -m 0644 "$SOURCE_DIR/deploy/50-stemcraft-console.rules" /etc/polkit-1/rules.d/50-stemcraft-console.rules
install -m 0755 "$SOURCE_DIR/deploy/stemcraft-console" /usr/local/sbin/stemcraft-console
chown -R stemcraft:stemcraft "$INSTALL_DIR"
systemctl daemon-reload
systemctl start stemcraft-console.service

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
  echo "The upgraded service did not become healthy. Roll back with: sudo $SOURCE_DIR/scripts/rollback.sh $BACKUP_DIR" >&2
  journalctl -u stemcraft-console.service --no-pager -n 30 >&2
  exit 1
fi

echo "Upgrade complete. Rollback files are in $BACKUP_DIR"
