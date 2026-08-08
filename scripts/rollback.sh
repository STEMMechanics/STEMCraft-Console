#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 || $# -ne 1 ]]; then
  echo "Usage: sudo $0 /var/lib/stemcraft-console/upgrades/TIMESTAMP" >&2
  exit 1
fi

INSTALL_DIR=/opt/stemcraft-console
BACKUP_ROOT=/var/lib/stemcraft-console/upgrades
BACKUP_DIR=$(realpath "$1")
case "$BACKUP_DIR" in
  "$BACKUP_ROOT"/*) ;;
  *) echo "Backup must be inside $BACKUP_ROOT." >&2; exit 1 ;;
esac

for item in app migrations alembic.ini requirements.txt; do
  [[ -e "$BACKUP_DIR/$item" ]] || { echo "Incomplete upgrade backup: missing $item" >&2; exit 1; }
done

systemctl stop stemcraft-console.service
cp -a "$BACKUP_DIR/app" "$BACKUP_DIR/migrations" "$BACKUP_DIR/alembic.ini" "$BACKUP_DIR/requirements.txt" "$INSTALL_DIR/"
if [[ -f "$BACKUP_DIR/stemcraft-console.db" ]]; then
  cp -a "$BACKUP_DIR/stemcraft-console.db" /var/lib/stemcraft-console/stemcraft-console.db
fi
"$INSTALL_DIR/.venv/bin/pip" install --requirement "$INSTALL_DIR/requirements.txt"
chown -R stemcraft:stemcraft "$INSTALL_DIR" /var/lib/stemcraft-console
systemctl start stemcraft-console.service
echo "Rollback complete."
