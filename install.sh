#!/usr/bin/env bash
set -euo pipefail

PREFIX="/usr/local"
LIBDIR="$PREFIX/lib/swap-manager"
BINDIR="$PREFIX/bin"
APPDIR="$PREFIX/share/applications"
ICONDIR="$PREFIX/share/icons/hicolor/scalable/apps"
POLKITDIR="/usr/share/polkit-1/actions"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Swap Manager to $PREFIX (root required)"

# Create directories
install -d "$LIBDIR" "$BINDIR" "$APPDIR" "$ICONDIR"

# Install core files
install -m 755 "$HERE/swapctl.sh" "$LIBDIR/swapctl.sh"
install -m 644 "$HERE/swap_manager_gui.py" "$LIBDIR/swap_manager_gui.py"
install -m 755 "$HERE/swap-manager" "$BINDIR/swap-manager"
install -m 644 "$HERE/requirements.txt" "$LIBDIR/requirements.txt"

# Desktop + icon
install -m 644 "$HERE/data/swap-manager.desktop" "$APPDIR/swap-manager.desktop"
install -m 644 "$HERE/data/icons/swap-manager.svg" "$ICONDIR/swap-manager.svg"

# Polkit policy
install -m 644 "$HERE/polkit/com.openai.swapmanager.policy" "$POLKITDIR/com.openai.swapmanager.policy"

# If a local venv exists, copy it alongside the installed app
if [ -d "$HERE/.venv" ]; then
  echo "Copying existing venv to $LIBDIR/.venv"
  # Remove any previous copy to avoid stale wheels
  rm -rf "$LIBDIR/.venv"
  cp -a "$HERE/.venv" "$LIBDIR/.venv"
fi

# Optionally build a venv in the install dir
if [ "${1:-}" = "--build-venv" ]; then
  echo "Building venv in $LIBDIR/.venv"
  python3 -m venv "$LIBDIR/.venv"
  "$LIBDIR/.venv/bin/pip" install --upgrade pip wheel
  if [ -f "$LIBDIR/requirements.txt" ]; then
    "$LIBDIR/.venv/bin/pip" install -r "$LIBDIR/requirements.txt"
  fi
fi

echo "Refreshing desktop and icon caches (if available)"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$PREFIX/share/applications" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f "$PREFIX/share/icons/hicolor" || true

echo "Done. Launch from your app menu as 'Swap Manager' or run: swap-manager"
