#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HERE/.venv"

python3 -m venv --system-site-packages "$VENV_DIR"

if [ -s "$HERE/requirements.txt" ]; then
  "$VENV_DIR/bin/pip" install -r "$HERE/requirements.txt"
fi

cat <<EOF
Venv created at: $VENV_DIR

To run with venv:
  $VENV_DIR/bin/python $HERE/swap_manager_gui.py

Or use the launcher which auto-detects the venv:
  $HERE/swap-manager
EOF
