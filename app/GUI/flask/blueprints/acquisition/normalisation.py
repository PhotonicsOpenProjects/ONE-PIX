"""Reference datacubes for the Normalisation tab of the Software settings.

A reference datacube is an ordinary measurement (acquisition + reconstruction with the current
settings) of a reference target, stored as it comes out of the reconstruction: the datacube is not
reduced to a spectrum. Each one is a pair of files in measure/reference_datacubes/:

    <name>.json        the reconstruction results, exactly as save_reconstruction_results() writes them
    <name>.meta.json   a small summary (date, imaging method, integration time, cube shape...) so that
                       listing the references never has to read the - possibly large - datacube
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from flask import jsonify, request, send_file

from i18n import register_translations
from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from onepix.progress import AcquisitionCancelled

from . import bp, tuning
from .routes import _run_started, _run_ended
from .normalisation_translations import TRANSLATIONS

register_translations(TRANSLATIONS)

logger = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def reference_dir():
    path = (
        Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        / "measure" / "reference_datacubes"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clean_name(raw):
    """A file-name-safe name: spaces and other characters become '_'. Empty -> timestamped default."""
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", (raw or "").strip()).strip("._-")[:64]
    return name or f"reference_{time.strftime('%Y%m%d_%H%M%S')}"


def _summary(name, results, acq_results, datacube_path):
    meta = results.get("metadata") or {}
    cube = results.get("reconstructed_data")
    shape = list(np.shape(cube)) if cube is not None else None
    wl = np.asarray(results.get("wavelengths", []), dtype=float)
    return {
        "name": name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "imaging_method_name": meta.get("imaging_method_name") or results.get("imaging_method_name"),
        "integration_time_ms": acq_results.get("integration_time_ms"),
        "scans_to_average": acq_results.get("spectro_scans2avg"),
        "shape": shape,
        "wavelength_min_nm": float(wl.min()) if wl.size else None,
        "wavelength_max_nm": float(wl.max()) if wl.size else None,
        "n_wavelengths": int(wl.size),
        "size_bytes": datacube_path.stat().st_size,
    }


@bp.route("/normalisation/list")
def normalisation_list():
    items = []
    for meta_path in sorted(reference_dir().glob("*.meta.json")):
        try:
            with open(meta_path, encoding="utf-8") as f:
                items.append(json.load(f))
        except (OSError, ValueError):
            logger.warning("Unreadable reference summary %s", meta_path)
    items.sort(key=lambda m: m.get("created", ""), reverse=True)
    return jsonify({"references": items})


@bp.route("/normalisation/run", methods=["POST"])
def normalisation_run():
    name = _clean_name((request.get_json(silent=True) or {}).get("name"))
    datacube_path = reference_dir() / f"{name}.json"
    if datacube_path.exists():
        return jsonify({"error": "exists", "name": name}), 409

    if not tuning.hardware_lock.acquire(blocking=False):
        return jsonify({"error": "busy"}), 409

    acq = None
    outcome, message = "error", None
    _run_started()
    try:
        acq = Acquisition()
        acq.init_measure()
        acq.thread_acquisition()

        rec = Reconstruction(acq.acquisition_results, plot_result=False)
        rec.data_reconstruction()
        rec.save_reconstruction_results(filename=datacube_path.name, save_path=reference_dir())

        summary = _summary(name, rec.reconstruction_results, acq.acquisition_results, datacube_path)
        with open(reference_dir() / f"{name}.meta.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=1)
        outcome = "success"
        return jsonify({"ok": True, "reference": summary})

    except AcquisitionCancelled as exc:
        logger.info("Reference acquisition cancelled: %s", exc)
        outcome, message = "cancelled", str(exc)
        datacube_path.unlink(missing_ok=True)
        return jsonify({"error": "cancelled", "message": message}), 499

    except Exception as exc:
        logger.exception("Error while acquiring a reference datacube")
        message = str(exc)
        datacube_path.unlink(missing_ok=True)
        return jsonify({"error": "failed", "message": message}), 500

    finally:
        try:
            if acq is not None:
                acq.close()
        finally:
            _run_ended(outcome, message)
            tuning.hardware_lock.release()


def _existing(name):
    """The datacube path of reference `name`, or None when the name is invalid or unknown."""
    if not name or not NAME_RE.match(name):
        return None
    path = reference_dir() / f"{name}.json"
    return path if path.exists() else None


@bp.route("/normalisation/delete", methods=["POST"])
def normalisation_delete():
    name = (request.get_json(silent=True) or {}).get("name")
    path = _existing(name)
    if path is None:
        return jsonify({"error": "not found"}), 404
    path.unlink()
    (reference_dir() / f"{name}.meta.json").unlink(missing_ok=True)
    return jsonify({"ok": True})


@bp.route("/normalisation/download/<name>")
def normalisation_download(name):
    path = _existing(name)
    if path is None:
        return jsonify({"error": "not found"}), 404
    return send_file(path, as_attachment=True, download_name=path.name, mimetype="application/json")
