from flask import render_template, Response, request, redirect, url_for, jsonify
from . import bp, controllers as ctl, tuning
from .field_meta import FIELD_META
from i18n import t
import gui_plugins
import zones

import io
import json
import orjson
import logging
import numpy as np
import cv2

from PIL import Image

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

import time

from pathlib import Path
from importlib.metadata import entry_points

from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from onepix.progress import progress as acquisition_progress
from onepix.progress import AcquisitionCancelled
from onepix.hardware.coregistration_lib import (
    capture_calibration_photo,
    save_coregistration_from_corners,
    hardware_json_path,
)

logger = logging.getLogger(__name__)

# The last /run's reconstruction_results, kept around only so a
# follow-up GET /acquisition/spectra can serve its spectra/wavelengths/
# cluster_name as JSON for an interactive client-side chart - /run
# itself only returns the rendered overlay image. Not every imaging
# method has per-cluster spectra (most work on a per-pixel datacube
# instead), so /spectra reports "no data" rather than erroring when
# these keys aren't present.
_last_reconstruction_results = None


# ----------------------------
# UTILS
# ----------------------------
def get_entrypoints(group_name):
    try:
        eps = entry_points()

        if hasattr(eps, "select"):
            eps = eps.select(group=group_name)
        else:
            eps = eps.get(group_name, [])

        return [ep.name for ep in eps]

    except Exception as e:
        logger.warning(f"Error loading {group_name}: {e}")
        return []


def json_default(obj):

    if isinstance(obj, np.ndarray):
        return obj.tolist()

    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, (np.floating,)):
        return float(obj)

    if isinstance(obj, np.bool_):
        return bool(obj)

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, (tuple, set)):
        return list(obj)

    if callable(obj):
        return f"<callable {obj.__name__}>"

    return str(obj)


# ----------------------------
# PAGES
# ----------------------------
@bp.route("/")
def acquisition_page():
    return render_template(
        "acquisition.html",
        overview=ctl.acquisition_overview()
    )


@bp.route("/hardware")
def hardware_page():

    return render_template(
        "settings_page.html",
        field_meta=FIELD_META,
        title=t("acquisition_settings.hardware_page_title"),
        category="hardware",
        data=ctl.hardware_settings(),
        plugins={
            "name_spectro": get_entrypoints("onepix.spectrometers"),
            "name_camera": get_entrypoints("onepix.cameras"),
        }
    )


@bp.route("/software")
def software_page():

    return render_template(
        "settings_page.html",
        field_meta=FIELD_META,
        title=t("acquisition_settings.software_page_title"),
        category="software",
        data=ctl.software_settings(),
        plugins={
            "imaging_method_name": get_entrypoints("onepix.imaging_methods")
        }
    )


@bp.route("/addon")
def addon_page():

    imaging_method_name = ctl.software_settings().get(
        "imaging_method_name"
    )

    # Fields, dropdown choices and panels specific to the selected
    # imaging method come from its own plugin, if it ships any.
    method_field_meta, method_choices, method_panels = (
        gui_plugins.method_settings(imaging_method_name)
    )

    return render_template(
        "settings_page.html",
        field_meta={**FIELD_META, **method_field_meta},
        title=t("acquisition_settings.addon_page_title"),
        category="addon",
        data=ctl.addon_settings(),
        plugins=method_choices,
        settings_panels=method_panels,
        imaging_method_name=imaging_method_name
    )


@bp.route("/imaging")
def imaging_page():
    return redirect(url_for("acquisition.addon_page"))


# ----------------------------
# SAVE SETTINGS
# ----------------------------
@bp.route("/save/<category>", methods=["POST"])
def save_settings(category):

    new_data = dict(request.form)

    ctl.save_settings(category, new_data)

    return redirect(url_for(f"acquisition.{category}_page", saved=1))


@bp.route("/save_addon", methods=["POST"])
def save_addon():

    sw = ctl.software_settings()
    method = sw.get("imaging_method_name")

    acq = Acquisition(imaging_method_name=method)

    acq.init_measure()

    path = acq.imaging_method.config_path

    new_data = dict(request.form)

    with open(path, "r") as f:
        old = json.load(f)

    for k, v in new_data.items():

        try:
            old[k] = json.loads(v)

        except:
            old[k] = v

    with open(path, "w") as f:
        json.dump(old, f, indent=2)

    return redirect(url_for("acquisition.addon_page", saved=1))


# ----------------------------
# PROGRESS (polled by the browser while /run is in flight)
# ----------------------------
@bp.route("/progress")
def acquisition_progress_route():
    return jsonify(acquisition_progress.snapshot())


# ----------------------------
# CANCEL (called from a separate request while /run is still in flight)
# ----------------------------
@bp.route("/cancel", methods=["POST"])
def cancel_acquisition():
    cancelled = acquisition_progress.request_cancel()
    return jsonify({"cancelled": cancelled})


# ----------------------------
# RUN ACQUISITION
# ----------------------------
@bp.route("/run")
def run_acquisition():
    global _last_reconstruction_results

    if not tuning.hardware_lock.acquire(blocking=False):
        return "The spectrometer/projector is in use by another acquisition.", 409

    try:
        acq = Acquisition()
        acq.init_measure()
        acq.thread_acquisition()

        rec = Reconstruction(
            acq.acquisition_results,
            plot_result=True
        )
        rec.data_reconstruction()

        rec.save_reconstruction_results() # ou ton vrai nom de fonction save core

        _last_reconstruction_results = rec.reconstruction_results

        img = rec.reconstruction_results.get("result2plot")

        if img is None:
            logger.error("No result2plot in reconstruction_results")
            return "No image to display", 500

        fig, ax = plt.subplots()
        ax.imshow(img, cmap="viridis")
        ax.axis("off")

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)

        return Response(buf.getvalue(), mimetype="image/png")

    except AcquisitionCancelled as e:
        logger.info("Acquisition cancelled by user: %s", e)
        return str(e), 499

    except Exception as e:
        print("ERREUR /run:", repr(e), flush=True)
        logger.exception("Error in /run acquisition route")
        return f"Error in /run: {e}", 500

    finally:
        tuning.hardware_lock.release()


# ----------------------------
# SPECTRA (for the interactive chart, alongside /run's overlay image)
# ----------------------------
@bp.route("/spectra")
def acquisition_spectra():
    results = _last_reconstruction_results

    if not results or "spectra" not in results or "wavelengths" not in results:
        return jsonify({"available": False})

    spectra = np.asarray(results["spectra"], dtype=float)
    wavelengths = np.asarray(results["wavelengths"], dtype=float)
    cluster_name = list(results.get("cluster_name") or [])

    # A NaN/Infinity reading (a saturated or dead spectrometer
    # channel) serializes via Python's json module as a bare NaN/
    # Infinity token - not valid JSON, so the browser's JSON.parse()
    # throws on it and the whole chart silently fails to load. null
    # is valid JSON and Plotly already renders it as a gap in the
    # line, which is the right treatment for an invalid reading.
    spectra = np.where(np.isfinite(spectra), spectra, None).tolist()
    wavelengths = np.where(np.isfinite(wavelengths), wavelengths, None).tolist()

    return jsonify({
        "available": True,
        "wavelengths": wavelengths,
        "spectra": spectra,
        "cluster_name": cluster_name,
    })


# ----------------------------
# ZONES (zone map of a zone-based result - see zones.py)
# ----------------------------
@bp.route("/zones")
def acquisition_zones():
    return jsonify(zones.summary(_last_reconstruction_results))


@bp.route("/zones/labels.png")
def acquisition_zone_labels():
    png = zones.label_map_png(_last_reconstruction_results)
    if png is None:
        return jsonify({"error": "No zones in the last acquisition"}), 404
    return Response(png, mimetype="image/png")


@bp.route("/zones/rgb.jpg")
def acquisition_zone_rgb():
    jpg = zones.rgb_jpeg(_last_reconstruction_results)
    if jpg is None:
        return jsonify({"error": "No zone photo in the last acquisition"}), 404
    return Response(jpg, mimetype="image/jpeg")


# ----------------------------
# HARDWARE SETTINGS — LIVE SPECTROMETER TUNING
# ----------------------------
@bp.route("/hardware/tuning/start", methods=["POST"])
def hardware_tuning_start():
    payload = request.get_json(silent=True) or {}

    try:
        state = tuning.session.start(payload.get("integration_time_ms"))
        return jsonify({"ok": True, **state})

    except tuning.TuningError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409

    except Exception as exc:
        logger.exception("Error starting spectrometer tuning")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/hardware/tuning/stop", methods=["POST"])
def hardware_tuning_stop():
    try:
        state = tuning.session.stop()
        return jsonify({"ok": True, **state})

    except Exception as exc:
        logger.exception("Error stopping spectrometer tuning")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/hardware/tuning/snapshot")
def hardware_tuning_snapshot():
    return jsonify({"ok": True, **tuning.session.snapshot()})


@bp.route("/hardware/tuning/integration_time", methods=["POST"])
def hardware_tuning_integration_time():
    payload = request.get_json(silent=True) or {}

    try:
        state = tuning.session.set_integration_time(
            payload.get("integration_time_ms")
        )
        return jsonify({"ok": True, **state})

    except tuning.TuningError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    except Exception as exc:
        logger.exception("Error updating spectrometer integration time")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/hardware/tuning/apply", methods=["POST"])
def hardware_tuning_apply():
    """Persist the tuned integration time into acquisition_parameters.json
    (the "software" settings category), the same file/JSON key the rest of
    the app already reads integration_time_ms from.

    Reuses ctl.get_config_path()/ctl.load_settings() (path resolution +
    reading the *full* current dict, so other keys like
    imaging_method_name are preserved) but writes the JSON directly rather
    than going through ctl.save_settings(): that helper's type-casting
    assumes string values straight out of an HTML <form> (dict(request.form))
    and errors on the native Python types (float/bool) a JSON API already
    has in hand."""
    payload = request.get_json(silent=True) or {}

    try:
        value = float(payload.get("integration_time_ms"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid integration time."}), 400

    if not (
        tuning.SpectrometerBridge.MIN_INTEGRATION_TIME_MS
        <= value
        <= tuning.SpectrometerBridge.MAX_INTEGRATION_TIME_MS
    ):
        return jsonify({"ok": False, "error": "Integration time out of range."}), 400

    path = ctl.get_config_path("software")
    if not path:
        return jsonify({"ok": False, "error": "No config path for 'software'."}), 500

    current = ctl.load_settings("software")
    current["integration_time_ms"] = value

    with open(path, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)

    return jsonify({"ok": True, "integration_time_ms": value})


# ----------------------------
# HARDWARE SETTINGS — PROJECTOR<->CAMERA COREGISTRATION (HAS), browser-driven
# ----------------------------
# The GUI's primary path: unlike calibrate_coregistration() above
# (which needs someone physically at this device's own screen to click
# corners in a local matplotlib window), these routes split that same
# calibration into a quick hardware step - project the reference
# pattern, photograph it - and a separate, hardware-free step - turn
# four clicked points into corregistration_array - so the corner-
# clicking itself can happen on the captured photo in any browser.
#
# While a calibration is in flight, corregistration_array is cleared
# in hardware_config.json (not left at its old, soon-to-be-replaced
# value) - creation_patterns()'s guard then correctly refuses any HAS
# acquisition that happens to run before the new one is confirmed,
# instead of silently segmenting on a photo that may no longer match
# what's about to be saved. The previous value is backed up in
# _pending_coregistration_backup and restored - never just left
# cleared - the moment this doesn't end in a confirmed save: a
# validation error in /corners, or the dialog being closed/abandoned
# (handled by /cancel, called both when the dialog is explicitly
# closed and, via sendBeacon, on page unload - see
# coregistration_calibration_panel.html).
#
# _pending_coregistration_photo holds the captured photo between the
# capture and corners requests. Only the capture step touches the
# camera/projector, so only it needs tuning.hardware_lock - held just
# for that one request, not across all of these, so an abandoned
# calibration can never leave the lock itself stuck held (independent
# of whatever happens to corregistration_array).

_pending_coregistration_photo = None
_pending_coregistration_backup = None


def _read_coregistration_fields():
    with open(hardware_json_path) as f:
        setup = json.load(f)
    return {
        "corregistration_array": setup.get("corregistration_array", []),
        "max_width": setup.get("max_width"),
        "max_height": setup.get("max_height"),
    }


def _write_coregistration_fields(fields):
    with open(hardware_json_path) as f:
        setup = json.load(f)
    setup.update(fields)
    with open(hardware_json_path, "w") as f:
        json.dump(setup, f, indent=4)


@bp.route("/hardware/coregistration/capture", methods=["POST"])
def coregistration_capture():

    if not tuning.hardware_lock.acquire(blocking=False):
        return jsonify({
            "error": "The spectrometer/projector is in use by another operation."
        }), 409

    global _pending_coregistration_photo, _pending_coregistration_backup

    # Re-capturing while already mid-calibration (dialog still open,
    # photo retaken) must not re-read hardware_config.json as "the
    # original" - it's already cleared from the first capture. Keep
    # the real backup from whichever capture started this session.
    backup = _pending_coregistration_backup or _read_coregistration_fields()

    try:
        _write_coregistration_fields({"corregistration_array": []})
        frame = capture_calibration_photo()
    except Exception as exc:
        logger.exception("coregistration capture failed")
        _write_coregistration_fields(backup)
        return jsonify({"error": str(exc)}), 500
    finally:
        tuning.hardware_lock.release()

    _pending_coregistration_photo = frame
    _pending_coregistration_backup = backup

    buf = io.BytesIO()

    Image.fromarray(
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    ).save(buf, format="PNG")

    buf.seek(0)

    return Response(buf.getvalue(), mimetype="image/png")


@bp.route("/hardware/coregistration/corners", methods=["POST"])
def coregistration_corners():

    global _pending_coregistration_photo, _pending_coregistration_backup

    if _pending_coregistration_photo is None:
        return jsonify({
            "error": "No calibration photo captured yet - capture one first."
        }), 400

    points = (request.json or {}).get("points")
    backup = _pending_coregistration_backup

    try:
        save_coregistration_from_corners(
            _pending_coregistration_photo,
            points
        )
    except (ValueError, TypeError) as exc:
        # Keep the old calibration rather than leaving it cleared.
        if backup is not None:
            _write_coregistration_fields(backup)
        return jsonify({"error": str(exc)}), 400
    finally:
        _pending_coregistration_photo = None
        _pending_coregistration_backup = None

    # The Hardware page's settings form holds these same fields - it
    # needs the new values, or its next Save would write the old
    # calibration back.
    return jsonify({"ok": True, "fields": _read_coregistration_fields()})


@bp.route("/hardware/coregistration/cancel", methods=["POST"])
def coregistration_cancel():
    """Restores the backed-up calibration if one is pending. Safe to
    call unconditionally (a no-op otherwise) - see
    coregistration_calibration_panel.html for when this fires."""

    global _pending_coregistration_photo, _pending_coregistration_backup

    if _pending_coregistration_backup is not None:
        _write_coregistration_fields(_pending_coregistration_backup)

    _pending_coregistration_photo = None
    _pending_coregistration_backup = None

    return jsonify({"ok": True})
