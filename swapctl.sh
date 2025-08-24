#!/usr/bin/env bash
set -euo pipefail

# swapctl.sh - privileged helper for swap management
#
# Commands:
#   enable <path>                 - swapon on path
#   disable <path>                - swapoff on path
#   create-file <path> <MiB> [--persist]
#                                 - create mkswap file, optionally add to /etc/fstab, swapon
#   delete-file <path> [--remove-fstab]
#                                 - swapoff, optional fstab cleanup, delete file (safety checks)
#   set-swappiness <value>        - set vm.swappiness now and persist via /etc/sysctl.d/99-swap-manager.conf
#   get-swappiness                - print current vm.swappiness

die() { echo "swapctl: $*" >&2; exit 1; }

need_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    die "this command requires root privileges"
  fi
}

is_swap_file_signature() {
  local p=$1
  command -v file >/dev/null 2>&1 || return 1
  local out
  out=$(file -b "$p" || true)
  [[ "$out" == *"swap file"* ]]
}

in_fstab_as_swap() {
  local p=$1
  grep -E "^[^#]*\s+$(printf '%q' "$p" | sed 's/[]\[\.^$*|?+(){}]/\\&/g')\s+none\s+swap\s" /etc/fstab >/dev/null 2>&1 || \
  grep -E "^[^#]*\s+$(printf '%q' "$p" | sed 's/[]\[\.^$*|?+(){}]/\\&/g')\s+swap\s" /etc/fstab >/dev/null 2>&1
}

cmd_enable() {
  need_root
  local target=${1:-}
  [[ -n "$target" ]] || die "enable: missing path"
  swapon --show=NAME | grep -Fxq "$target" && { echo "already enabled"; exit 0; }
  swapon "$target"
}

cmd_disable() {
  need_root
  local target=${1:-}
  [[ -n "$target" ]] || die "disable: missing path"
  swapoff "$target"
}

cmd_create_file() {
  need_root
  local path=${1:-}
  local size_mib=${2:-}
  local persist=${3:-}
  [[ -n "$path" && -n "$size_mib" ]] || die "create-file: usage: create-file <path> <MiB> [--persist]"
  [[ "$size_mib" =~ ^[0-9]+$ ]] || die "create-file: size must be an integer MiB"
  if [[ -e "$path" ]]; then
    die "create-file: path exists: $path"
  fi
  # Create sparse file via fallocate if available, else dd
  if command -v fallocate >/dev/null 2>&1; then
    fallocate -l "${size_mib}M" "$path"
  else
    dd if=/dev/zero of="$path" bs=1M count=0 seek="$size_mib" status=progress
  fi
  chmod 600 "$path"
  mkswap "$path"
  # Persist if requested
  if [[ "$persist" == "--persist" ]]; then
    if ! in_fstab_as_swap "$path"; then
      echo -e "$path	none	swap	sw	0	0" >> /etc/fstab
    fi
  fi
  swapon "$path"
}

cmd_delete_file() {
  need_root
  local path=${1:-}
  local remove_fstab=${2:-}
  [[ -n "$path" ]] || die "delete-file: usage: delete-file <path> [--remove-fstab]"
  # Only allow deletion of regular files, and only if they look like swap or listed in fstab
  [[ -f "$path" ]] || die "delete-file: not a regular file: $path"
  if ! is_swap_file_signature "$path" && ! in_fstab_as_swap "$path"; then
    die "delete-file: refusing to delete non-swap file not in fstab"
  fi
  # Try to disable; ignore error if already off
  if swapon --show=NAME | grep -Fxq "$path"; then
    swapoff "$path" || true
  fi
  if [[ "$remove_fstab" == "--remove-fstab" ]]; then
    # Remove matching lines from /etc/fstab
    tmpf=$(mktemp)
    sed -E "/^[^#]*\s+$(printf '%q' "$path" | sed 's/[]\[\.^$*|?+(){}]/\\&/g')\s+(none\s+)?swap\s/d" /etc/fstab > "$tmpf"
    cat "$tmpf" > /etc/fstab
    rm -f "$tmpf"
  fi
  rm -f "$path"
}

cmd_set_swappiness() {
  need_root
  local val=${1:-}
  [[ "$val" =~ ^[0-9]+$ ]] || die "set-swappiness: value must be integer 0-200"
  sysctl vm.swappiness="$val"
  mkdir -p /etc/sysctl.d
  echo "vm.swappiness = $val" > /etc/sysctl.d/99-swap-manager.conf
  # Apply just this file if possible, otherwise system-wide reload
  if command -v sysctl >/dev/null 2>&1; then
    sysctl -p /etc/sysctl.d/99-swap-manager.conf >/dev/null 2>&1 || sysctl --system >/dev/null 2>&1 || true
  fi
}

cmd_get_swappiness() {
  cat /proc/sys/vm/swappiness
}

case ${1:-} in
  enable) shift; cmd_enable "$@" ;;
  disable) shift; cmd_disable "$@" ;;
  create-file) shift; cmd_create_file "$@" ;;
  delete-file) shift; cmd_delete_file "$@" ;;
  set-swappiness) shift; cmd_set_swappiness "$@" ;;
  get-swappiness) shift; cmd_get_swappiness "$@" ;;
  *)
    cat >&2 <<EOF
Usage: $0 <command> [args]

Commands:
  enable <path>
  disable <path>
  create-file <path> <MiB> [--persist]
  delete-file <path> [--remove-fstab]
  set-swappiness <value>
  get-swappiness
EOF
    exit 2
    ;;
esac

