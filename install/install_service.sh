#!/usr/bin/env bash
# Run as the desktop user, from a terminal in the Raspberry Pi desktop.
set -euo pipefail

if [[ ${1:-} == --help ]]; then
    echo 'Usage: bash install/install_service.sh [path/to/python]'
    echo 'Install and start the ONE-PIX user service from a graphical session (no sudo).'
    exit 0
fi
if (( $# > 1 )); then
    echo 'Expected at most one Python executable argument.' >&2
    exit 1
fi
if [[ $EUID == 0 ]]; then
    echo 'Run this script as the desktop user, without sudo.' >&2
    exit 1
fi
if [[ -z ${DISPLAY:-} ]]; then
    echo 'Run this script in a desktop terminal with DISPLAY set (X11 or XWayland).' >&2
    exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/.." && pwd)"
python_bin="$(command -v -- "${1:-python}")"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

systemctl --user show-environment >/dev/null
# Fail before installing a unit if the selected environment lacks GUI dependencies.
"$python_bin" -B -c 'import flask, onepix, onepix_plugins_manager, screeninfo; assert screeninfo.get_monitors(), "No display detected"'

"$python_bin" -B - "$script_dir/onepix.service.in" "$repo_dir" "$python_bin" "$unit_dir" <<'PY'
import os
from pathlib import Path
import sys

template, repo, python, destination = sys.argv[1:]

def quote(value, command=False):
    # systemd uses its own quoting and percent specifiers, not shell quoting.
    if any(char in value for char in '\n\r\x00'):
        raise ValueError('Paths must not contain newlines or NUL')
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    if command:
        value = value.replace('$', '$$')
    return '"' + value + '"'

unit = Path(template).read_text(encoding='utf-8')
unit = unit.replace('@WORKDIR@', quote(os.path.abspath(repo)))
unit = unit.replace('@PYTHON@', quote(os.path.abspath(python), command=True))
target = Path(destination)
target.mkdir(parents=True, exist_ok=True)
(target / 'onepix.service').write_text(unit, encoding='utf-8')
PY

# Do not copy unrelated variables or credentials into the user manager.
for variable in DISPLAY XAUTHORITY WAYLAND_DISPLAY XDG_RUNTIME_DIR; do
    if [[ -v $variable ]]; then
        systemctl --user import-environment "$variable"
    else
        systemctl --user unset-environment "$variable"
    fi
done
systemctl --user daemon-reload
systemctl --user enable onepix.service
systemctl --user restart onepix.service
systemctl --user status onepix.service --no-pager
echo 'Logs: journalctl --user -u onepix.service -f'
