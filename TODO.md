# Development roadmap

The macOS development backend owns Minecraft subprocesses, while production
uses systemd-owned instances so Minecraft remains available across panel
restarts. The API and frontend expose the same controls for both backends.

## Completed

- [x] Change or upgrade the Paper JAR with checksum verification and atomic replacement.
- [x] Configure per-server JAR filename, memory allocation, and additional Java startup options.
- [x] Add database migrations that work for clean installations.
- [x] Add a production installer with Ubuntu and Oracle Linux support.
- [x] Add a one-line remote installation entry point.
- [x] Add documented upgrade, rollback, uninstall, and service-management workflows.
- [x] Add a systemd process backend so Minecraft continues running across panel restarts.
- [x] Add scheduled backups with retention policies.
- [x] Add scheduled console commands with audit history.
- [x] Persist and graph historical CPU, memory, player, and uptime metrics.
- [x] Add a verified, rollback-capable console self-update workflow.

## Engineering notes

New process backends must not invoke a shell and must validate service names,
JAR paths, and user-supplied JVM options. Scheduled jobs should use durable
database state rather than in-process timers alone.
