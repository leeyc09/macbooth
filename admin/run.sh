#!/usr/bin/env bash
# Launch the pibooth template admin using the pibooth virtualenv if present.
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PIBOOTH_PYTHON:-$HOME/pibooth-venv/bin/python}"
[ -x "$PY" ] || PY="python3"
exec "$PY" "$DIR/admin/pibooth_admin.py" "$@"
