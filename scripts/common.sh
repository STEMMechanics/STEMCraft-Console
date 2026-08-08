#!/usr/bin/env bash

if [[ -t 1 ]]; then
  STEMCRAFT_BLUE=$'\033[1;34m'
  STEMCRAFT_GREEN=$'\033[1;32m'
  STEMCRAFT_YELLOW=$'\033[1;33m'
  STEMCRAFT_RED=$'\033[1;31m'
  STEMCRAFT_BOLD=$'\033[1m'
  STEMCRAFT_RESET=$'\033[0m'
else
  STEMCRAFT_BLUE=
  STEMCRAFT_GREEN=
  STEMCRAFT_YELLOW=
  STEMCRAFT_RED=
  STEMCRAFT_BOLD=
  STEMCRAFT_RESET=
fi

banner() {
  printf '\n%s%s============================================================%s\n' "$STEMCRAFT_BLUE" "$STEMCRAFT_BOLD" "$STEMCRAFT_RESET"
  printf ' %s%s%s\n' "$STEMCRAFT_BOLD" "$1" "$STEMCRAFT_RESET"
  printf '%s%s============================================================%s\n\n' "$STEMCRAFT_BLUE" "$STEMCRAFT_BOLD" "$STEMCRAFT_RESET"
}

section() { printf '\n%s==>%s %s%s%s\n' "$STEMCRAFT_BLUE" "$STEMCRAFT_RESET" "$STEMCRAFT_BOLD" "$*" "$STEMCRAFT_RESET"; }
info() { printf '%s[INFO]%s  %s\n' "$STEMCRAFT_GREEN" "$STEMCRAFT_RESET" "$*"; }
warn() { printf '%s[WARN]%s  %s\n' "$STEMCRAFT_YELLOW" "$STEMCRAFT_RESET" "$*" >&2; }
error() { printf '%s[ERROR]%s %s\n' "$STEMCRAFT_RED" "$STEMCRAFT_RESET" "$*" >&2; }
die() { error "$*"; exit 1; }
