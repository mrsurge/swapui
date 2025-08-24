Swap Manager (GTK + Bash)

Overview

- A simple GTK3 GUI (Python) to manage Linux swap on modern Debian.
- A Bash helper runs privileged actions: create/enable/disable/delete swapfiles, edit fstab, and set swappiness.

Features

- List active swap devices/files and usage.
- Enable/disable selected swap entry.
- Create a swap file (size, path, optional fstab persist) and activate it.
- Remove a swap file (deactivate, optional fstab cleanup, then delete).
- View and set vm.swappiness (with persistence via /etc/sysctl.d/99-swap-manager.conf).

Requirements (Debian/Ubuntu)

- Python 3
- System GTK libs (needed even with venv): `gir1.2-gtk-3.0` and `libgirepository1.0-dev`
- PolicyKit for privilege escalation: `policykit-1`

Run

- From this folder:

  - GUI: `python3 swap_manager_gui.py`
  - If you run as a regular user, privileged actions will be invoked via `pkexec` (you may be prompted). If you run the GUI as root, it will call the helper directly.

Notes

- Ensure the helper is executable: `chmod +x swapctl.sh` (done in repo).
- If `pkexec` prompts don’t appear in your desktop session, you can run the GUI as root: `sudo -E python3 swap_manager_gui.py`.
- The GUI reads `/proc/swaps` directly for listing; privileged actions only go through the helper.

Python Virtual Environment

- Create a project-local venv and install Python deps:
  - `./setup_venv.sh`
- Run via launcher (auto-detects `.venv`):
  - `./swap-manager`
- Or explicitly:
  - `.venv/bin/python swap_manager_gui.py`

Notes on venv and GTK

- The venv is created with `--system-site-packages` so it can import `gi` from system packages. Nothing is installed from PyPI unless you add extra packages to `requirements.txt`.

System Install with Venv

- Copy app system-wide and reuse/build a venv alongside the installed files:
  - Reuse existing local venv: `sudo ./install.sh`
  - Build venv in install dir: `sudo ./install.sh --build-venv`
  - Launch from menu as “Swap Manager” or run `swap-manager`.

Files

- `swap_manager_gui.py` — Python GTK3 app.
- `swapctl.sh` — Bash helper for privileged operations.

Security Notes

- Deleting swap files is restricted to regular files that identify as swap by the `file(1)` signature or that are listed in `/etc/fstab` as swap entries.
- The tool does not delete or repartition block devices; it only enables/disables them.

Common Tasks

- Create and persist a 2 GiB swap file at `/swapfile`:

  - In the GUI, set Path `/swapfile`, Size `2048` MiB, check `Persist in fstab`, then Create.

- Change swappiness to 10 and persist:

  - In the GUI, set Swappiness to `10`, click Apply. This writes `/etc/sysctl.d/99-swap-manager.conf` and applies it immediately.

Uninstall / Cleanup

- Remove `/etc/sysctl.d/99-swap-manager.conf` if you no longer want a persistent swappiness override, then reload with `sudo sysctl --system`.
