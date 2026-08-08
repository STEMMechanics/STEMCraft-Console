#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 || ${1:-} != "--confirm" ]]; then
  echo "Usage: sudo $0 --confirm" >&2
  echo "Application files are removed; server and database data are preserved." >&2
  exit 1
fi

systemctl disable --now stemcraft-console.service 2>/dev/null || true
rm -f /etc/systemd/system/stemcraft-console.service /etc/systemd/system/stemcraft-server@.service
rm -f /etc/polkit-1/rules.d/50-stemcraft-console.rules
rm -f /usr/local/sbin/stemcraft-console
systemctl daemon-reload
rm -rf /opt/stemcraft-console
echo "Removed application files. /var/lib/stemcraft-console, /srv/minecraft and /etc/stemcraft-console were preserved."
