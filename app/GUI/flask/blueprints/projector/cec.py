"""HDMI-CEC control of the video projector, through libcec's `cec-client`.

The bench drives its projector over HDMI; when the projector supports
CEC, the Raspberry Pi can switch it on / to standby and read what the
projector says about itself (vendor, name, power status...) on the same
cable - no extra wiring, and nothing to install beyond the `cec-utils`
package (`sudo apt install cec-utils`).

Every call runs one short-lived `cec-client -s` (single-command mode):
the command goes in on stdin, the answer comes back on stdout. That is
exactly the command line used by hand on the bench::

    echo 'on 0' | cec-client -s -d 8 /dev/cec1

Configuration (optional keys in conf/hardware_config.json):

- ``cec_device``  : CEC adapter, default ``/dev/cec1`` (HDMI 1 on a Pi 4)
- ``cec_address`` : projector's CEC logical address, default ``0``
  (the "TV" slot - where a display/projector normally sits)
- ``cec_standby`` : ``true`` if the projector obeys the CEC Standby
  command, default ``false``. Many projectors with a minimal CEC chip
  (vendor id 00:00:00) accept "on" but silently ignore every way of
  switching them off - the PA503X of the bench is one of them (tested:
  standby to the projector, broadcast standby, Power and Power Off keys).
"""

import json
import logging
import os
import re
import shutil
import subprocess
import threading

logger = logging.getLogger(__name__)

DEFAULT_DEVICE = "/dev/cec1"
DEFAULT_ADDRESS = "0"

_HARDWARE_JSON = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "..",
        "conf", "hardware_config.json",
    )
)

# cec-client grabs the adapter exclusively: two concurrent calls would
# make the second one fail, so every call goes through this lock.
_cec_lock = threading.Lock()


class CecError(RuntimeError):
    """User-facing CEC error (tool missing, timeout, adapter busy...)."""


def _read_conf():
    try:
        with open(_HARDWARE_JSON) as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        logger.warning("CEC config: could not read %s (%s)", _HARDWARE_JSON, exc)
        return {}


def standby_supported():
    return _read_conf().get("cec_standby", False) is True


def get_config():
    """(device, logical_address), validated - they end up on a command
    line, so anything unexpected falls back to the defaults."""
    conf = _read_conf()
    device = str(conf.get("cec_device", DEFAULT_DEVICE))
    address = str(conf.get("cec_address", DEFAULT_ADDRESS))

    if not re.fullmatch(r"/dev/cec\d+", device):
        logger.warning("CEC config: invalid cec_device %r, using default", device)
        device = DEFAULT_DEVICE
    if not re.fullmatch(r"[0-9a-fA-F]", address):
        logger.warning("CEC config: invalid cec_address %r, using default", address)
        address = DEFAULT_ADDRESS
    return device, address


def is_available():
    return shutil.which("cec-client") is not None


def _run(command, debug_level="1", timeout_s=15.0):
    """Send one command to cec-client and return its stdout."""
    if not is_available():
        raise CecError("cec-client not found - install it with: sudo apt install cec-utils")

    device, _ = get_config()

    if not _cec_lock.acquire(timeout=timeout_s):
        raise CecError("The CEC adapter is busy with another command.")
    try:
        logger.info("CEC: %r on %s", command, device)
        result = subprocess.run(
            ["cec-client", "-s", "-d", debug_level, device],
            input=command + "\n",
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        raise CecError(f"No answer from cec-client after {timeout_s:.0f} s.")
    finally:
        _cec_lock.release()

    output = (result.stdout or "") + (result.stderr or "")
    if "could not open a connection" in output.lower() or "unable to open" in output.lower():
        raise CecError(
            f"Could not open {device}: check the HDMI port and that the "
            "app's user is in the 'video' group."
        )
    if result.returncode != 0:
        raise CecError(output.strip()[-300:] or f"cec-client exited with {result.returncode}")
    return result.stdout


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------

def power_on():
    _, address = get_config()
    _run(f"on {address}", debug_level="8")


def standby():
    _, address = get_config()
    _run(f"standby {address}", debug_level="8")


def power_status():
    """'on', 'standby', 'in transition from standby to on', ... or 'unknown'."""
    _, address = get_config()
    out = _run(f"pow {address}")
    match = re.search(r"power status:\s*(.+)", out)
    return match.group(1).strip() if match else "unknown"


_SCAN_FIELDS = {
    "address": "address",
    "active source": "active_source",
    "vendor": "vendor",
    "osd string": "osd_name",
    "cec version": "cec_version",
    "power status": "power_status",
    "language": "language",
}


def scan():
    """Every device answering on the CEC bus, as a list of dicts.

    Parses `cec-client`'s `scan` report, made of blocks like::

        device #0: TV
        address:       0.0.0.0
        vendor:        Optoma
        osd string:    PA503X
        CEC version:   1.4
        power status:  standby
    """
    out = _run("scan", timeout_s=30.0)
    devices, current = [], None
    for line in out.splitlines():
        head = re.match(r"device #(\w+):\s*(.*)", line.strip())
        if head:
            current = {"logical_address": head.group(1), "type": head.group(2).strip()}
            devices.append(current)
            continue
        if current is None or ":" not in line:
            continue
        key, _, value = line.partition(":")
        field = _SCAN_FIELDS.get(key.strip().lower())
        if field:
            current[field] = value.strip()
    return devices
