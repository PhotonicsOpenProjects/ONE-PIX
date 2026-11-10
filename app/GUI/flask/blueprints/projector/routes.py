import logging

from flask import jsonify

from . import bp
from . import cec
from blueprints.acquisition.tuning import hardware_lock

logger = logging.getLogger(__name__)


def _error(exc, status=500):
    logger.warning("Projector: %s", exc)
    return jsonify({"ok": False, "error": str(exc)}), status


# ----------------------------------------------------------------------
# POWER (HDMI-CEC)
# ----------------------------------------------------------------------

@bp.route("/api/power/on", methods=["POST"])
def api_power_on():
    try:
        cec.power_on()
    except cec.CecError as exc:
        return _error(exc)
    return jsonify({"ok": True})


@bp.route("/api/power/standby", methods=["POST"])
def api_power_standby():
    # Switching the projector off mid-acquisition would silently ruin the
    # measurement: refuse while the acquisition/tuning lock is held.
    if not cec.standby_supported():
        return _error("This projector ignores CEC standby (cec_standby is false).", 409)
    if hardware_lock.locked():
        return _error("An acquisition is running - standby refused.", 409)
    try:
        cec.standby()
    except cec.CecError as exc:
        return _error(exc)
    return jsonify({"ok": True})


@bp.route("/api/power")
def api_power_status():
    try:
        status = cec.power_status()
    except cec.CecError as exc:
        return _error(exc)
    return jsonify({"ok": True, "status": status})


# ----------------------------------------------------------------------
# INFO
# ----------------------------------------------------------------------

@bp.route("/api/cec")
def api_cec_info():
    """CEC configuration + every device answering on the bus."""
    device, address = cec.get_config()
    info = {
        "ok": True,
        "available": cec.is_available(),
        "device": device,
        "address": address,
        "devices": [],
    }
    if info["available"]:
        try:
            info["devices"] = cec.scan()
        except cec.CecError as exc:
            info["ok"] = False
            info["error"] = str(exc)
    return jsonify(info)


@bp.route("/api/display")
def api_display_info():
    """What the OS sees on HDMI: the monitors, which one ONE-PIX projects
    on (same rule as Projection.get_display_configuration()) and the
    refresh rate that sets the integration-time floor."""
    try:
        import screeninfo
        from onepix.hardware.Projection import get_display_configuration
        from onepix.hardware.display_timing import get_refresh_rate_hz

        _, projector_monitor = get_display_configuration()
        monitors = [
            {
                "name": m.name,
                "width": m.width,
                "height": m.height,
                "x": m.x,
                "y": m.y,
                "is_primary": bool(getattr(m, "is_primary", False)),
                "is_projector": (m.x, m.y, m.name) == (
                    projector_monitor.x, projector_monitor.y, projector_monitor.name
                ),
            }
            for m in screeninfo.get_monitors()
        ]
        return jsonify({
            "ok": True,
            "monitors": monitors,
            "refresh_rate_hz": get_refresh_rate_hz(),
        })
    except Exception as exc:  # no desktop session, missing lib...
        return _error(exc)
