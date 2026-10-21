#!/usr/bin/env bash
# Install the system service, including from SSH.
set -euo pipefail
if [[ ${1:-} == --help ]]; then
    echo 'Usage: bash install/install_service.sh [path/to/python]'
    echo 'Install, enable and restart the system service; sudo is requested.'
    exit 0
fi
if (( $# > 1 )); then
    echo 'Expected at most one Python executable argument.' >&2
    exit 1
fi
service_user="${SUDO_USER:-$(id -un)}"
if [[ $service_user == root ]]; then
    echo 'Run as the application user, or use sudo from that user.' >&2
    exit 1
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/.." && pwd)"
python_bin="$(command -v -- "${1:-python}")"
privilege=()
if [[ $EUID != 0 ]]; then
    sudo -v
    privilege=(sudo)
fi
temporary_unit="$(mktemp)"
trap 'rm -f -- "$temporary_unit"' EXIT
"$python_bin" -B - "$script_dir/onepix.service" "$repo_dir" "$python_bin" "$service_user" "$temporary_unit" <<'PY'
import os
from pathlib import Path
import re
import sys

template, repo, python, user, destination = sys.argv[1:]

def quote(value, command=False):
    if any(char in value for char in '\n\r\x00'):
        raise ValueError('Paths must not contain newlines or NUL')
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    if command:
        value = value.replace('$', '$$')
    return '"' + value + '"'

unit = Path(template).read_text(encoding='utf-8')
settings = {
    'User': quote(user),
    'WorkingDirectory': quote(os.path.abspath(repo)),
    'ExecStart': quote(os.path.abspath(python), command=True) + ' -u ' + quote(os.path.join(repo, 'app/GUI/flask/run.py'), command=True),
}
for key, value in settings.items():
    unit = re.sub(r'^' + key + r'=.*$', lambda match: key + '=' + value, unit, flags=re.MULTILINE)
Path(destination).write_text(unit, encoding='utf-8')
PY
# Stop the previous user service, if present, to release port 5000.
if [[ $EUID != 0 ]] && systemctl --user cat onepix.service >/dev/null 2>&1; then
    systemctl --user disable --now onepix.service
fi
"${privilege[@]}" install -m 644 "$temporary_unit" /etc/systemd/system/onepix.service
"${privilege[@]}" systemctl daemon-reload
"${privilege[@]}" systemctl enable onepix.service
"${privilege[@]}" systemctl restart onepix.service
"${privilege[@]}" systemctl status onepix.service --no-pager
echo 'Logs: sudo journalctl -u onepix.service -f'
