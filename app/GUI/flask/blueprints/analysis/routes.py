from flask import (
    render_template,
    jsonify,
    request,
    Response
)

from . import bp
from . import state

import collections.abc
import json
import io
import copy
import importlib
import logging
import threading
import time
import types
import typing
import warnings

import numpy as np

from PIL import Image

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from pathlib import Path

from spectra_core.plugins.discovery import (
    discover_transforms,
    discover_analyses
)

from spectra_core.plugins.registry import (
    TRANSFORMS,
    ANALYSES
)

from onepix.Analysis import Analysis
from onepix.ImagingMethodBridge import ImagingMethodBridge
from onepix import utils as onepix_utils

from security import safe_path

import zones


logger = logging.getLogger(__name__)
SPECIFIC_ANALYSIS_METHODS = set()


# ==========================================
# DISCOVER PLUGINS
# ==========================================

# Held while the registry is rebuilt and while a pipeline runs on it,
# so a run never sees it half-filled.
_registry_lock = threading.Lock()


def refresh_plugins():
    """(Re)discover the spectra_core transforms and analyses, so plugins
    installed or removed from the Plugins page show up here without
    restarting the app. An already loaded plugin keeps its code until
    then, though: updating one still needs a restart.

    If discovery fails (a broken plugin), the previous registry is kept.
    """

    with _registry_lock:

        previous = dict(TRANSFORMS), dict(ANALYSES)

        try:

            importlib.invalidate_caches()
            TRANSFORMS.clear()
            ANALYSES.clear()
            discover_transforms()
            discover_analyses()

        except Exception:

            logger.exception("Analysis plugin discovery failed")
            TRANSFORMS.clear()
            ANALYSES.clear()
            TRANSFORMS.update(previous[0])
            ANALYSES.update(previous[1])


refresh_plugins()


# ==========================================
# UTILS
# ==========================================

def get_measure_path():

    return (
        Path(__file__)
        .resolve()
        .parent.parent.parent.parent.parent.parent
        / "measure"
    )


def get_reference_dir():
    """Where captured reflectance-reference spectra (one small JSON
    each - {"wavelengths": [...], "spectrum": [...]}) are stored, so
    reflectance_normalization's reference_path parameter can point to
    one. Lives under measure/ rather than next to it so it's covered
    by the same backup/retention expectations as everything else
    there."""

    reference_dir = get_measure_path() / "references"

    reference_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    return reference_dir


def save_reference_spectrum(spectrum, wavelengths):
    """Written as plain JSON (not via onepix_utils.save_dict_json,
    whose serialize_for_json wraps ndarrays as
    {"__type__": "ndarray", ...} for ONE-PIX's own internal round-
    tripping) - reflectance_normalization.transform() is an external
    plugin that reads this file with a plain json.load() and expects
    exactly {"wavelengths": [...], "spectrum": [...]}."""

    filename = (
        f"reference_{time.strftime('%Y%m%d_%H%M%S')}.json"
    )

    filepath = get_reference_dir() / filename

    with open(filepath, "w", encoding="utf-8") as f:

        json.dump(
            {
                "wavelengths": np.asarray(wavelengths).tolist(),
                "spectrum": np.asarray(spectrum).tolist(),
            },
            f
        )

    return filepath


def image_response(img):

    img = np.array(img)

    img = img.astype(
        np.uint8
    )

    fig, ax = plt.subplots(
        figsize=(12, 6)
    )

    ax.imshow(img)

    # Integer-only pixel graduations (row/column indices), never
    # fractional ticks, regardless of image size.
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_xlabel("Column")
    ax.set_ylabel("Row")

    ax.tick_params(colors="#5a6270", labelsize=9)
    ax.xaxis.label.set_color("#16191f")
    ax.yaxis.label.set_color("#16191f")

    for spine in ax.spines.values():
        spine.set_color("#c9ced6")

    plt.tight_layout()

    buf = io.BytesIO()

    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        dpi=140
    )

    buf.seek(0)

    plt.close(fig)

    return Response(
        buf.getvalue(),
        mimetype="image/png"
    )


# ==========================================
# PAGE
# ==========================================

@bp.route("/")
def analysis_page():

    return render_template(
        "analysis.html"
    )


# ==========================================
# PLUGINS
# ==========================================

@bp.route("/plugins")
def plugins():

    # Fetched once per visit of the Analysis page.
    refresh_plugins()

    return jsonify({

        "transforms": list(
            TRANSFORMS.keys()
        ),

        "analyses": list(
            ANALYSES.keys()
        )
    })


# ==========================================
# PLUGIN INFO
# ==========================================

@bp.route("/plugin/<name>")
def plugin_info(name):

    if name in TRANSFORMS:

        plugin = TRANSFORMS[name]

    elif name in ANALYSES:

        plugin = ANALYSES[name]

    else:

        return jsonify({
            "error": "Plugin not found"
        }), 404

    params = []

    for param_name, meta in plugin["params"].items():

        param = {

            "name": param_name,

            "default": meta["default"],

            "type": meta["type"]
        }

        choices, multiple = param_choices(plugin["fn"], param_name)

        if choices is not None:

            param["choices"] = choices
            param["multiple"] = multiple

        params.append(param)

    return jsonify({

        "name": name,

        "params": params
    })


def param_choices(fn, name):
    """(choices, multiple) a plugin parameter's type annotation offers,
    so the page shows a menu instead of a free-text field:
    Literal["a", "b"] for one of them, List[Literal["a", "b"]] (or
    Tuple, Set, Sequence) for any of them, Optional[...] either way.
    (None, False) otherwise."""

    try:
        hint = typing.get_type_hints(fn).get(name)
    except Exception:
        return None, False

    def without_none(hint):
        if typing.get_origin(hint) in (typing.Union, types.UnionType):
            args = [arg for arg in typing.get_args(hint) if arg is not type(None)]
            if len(args) == 1:
                return args[0]
        return hint

    hint = without_none(hint)

    if typing.get_origin(hint) is typing.Literal:
        return list(typing.get_args(hint)), False

    if typing.get_origin(hint) in (list, tuple, set, frozenset, collections.abc.Sequence, collections.abc.Collection, collections.abc.Iterable):
        args = typing.get_args(hint)
        item = without_none(args[0]) if args else None
        if typing.get_origin(item) is typing.Literal:
            return list(typing.get_args(item)), True

    return None, False


# ==========================================
# LIST MEASURES
# ==========================================

@bp.route("/measures")
def measures():

    save_path = get_measure_path()

    if not save_path.exists():

        return jsonify([])

    files = sorted(
        save_path.glob("*.json"),
        reverse=True
    )

    filenames = [
        f.name
        for f in files
    ]

    return jsonify(filenames)


@bp.route("/load", methods=["POST"])
def load_measure():

    filename = request.json.get(
        "filename"
    )

    save_path = get_measure_path()

    filepath = safe_path(save_path, filename)

    if filepath is None or not filepath.exists():

        return jsonify({
            "error": "File not found"
        }), 404

    analysis = Analysis(
        reconstruction_dict=filepath,
        plot_result=False
    )

    data = analysis.reconstruction_dict

    state.CURRENT_RECONSTRUCTION = (
        copy.deepcopy(data)
    )

    state.ORIGINAL_RESULT = (
        copy.deepcopy(data)
    )

    state.CURRENT_RESULT = (
        copy.deepcopy(data)
    )

    img = data.get(
        "result2plot"
    )

    if img is None:

        return jsonify({
            "error": "No result2plot found"
        }), 500

    return image_response(img)


# ==========================================
# APPLY PIPELINE
# ==========================================

@bp.route("/run", methods=["POST"])
def run_analysis():

    if state.CURRENT_RESULT is None:

        return "No reconstruction loaded", 400

    payload = request.json

    steps = payload.get(
        "steps",
        []
    )

    analysis = Analysis(
        reconstruction_dict=state.CURRENT_RESULT,
        plot_result=True
    )

    with _registry_lock:

        analysis.data_analysis(
            steps
        )

    state.CURRENT_RESULT = (
        copy.deepcopy(
            analysis.analysis_results
        )
    )

    img = analysis.analysis_results.get(
        "result2plot"
    )

    if img is None:

        return "No result image", 500

    return image_response(img)


# ==========================================
# SPECTRA (for the interactive chart, alongside /run's overlay image)
# ==========================================

@bp.route("/spectra")
def analysis_spectra():

    result = state.CURRENT_RESULT

    if (
        not result
        or "spectra" not in result
        or "wavelengths" not in result
    ):
        return jsonify({"available": False})

    spectra = np.asarray(result["spectra"], dtype=float)
    wavelengths = np.asarray(result["wavelengths"], dtype=float)
    cluster_name = list(result.get("cluster_name") or [])

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


# ==========================================
# ANALYSIS OUTPUTS (values computed by analysis steps - see
# onepix.Analysis.tabulate_outputs())
# ==========================================

# Up to this many spectra, every one gets its own row; past that (a
# per-pixel result) the table summarizes each output instead.
MAX_OUTPUT_ROWS = 100


def _json_numbers(values):
    values = np.asarray(values, dtype=float)
    return np.where(np.isfinite(values), values, None).tolist()


@bp.route("/outputs")
def analysis_outputs():

    result = state.CURRENT_RESULT
    outputs = (result or {}).get("analysis_outputs")

    if not outputs or not len(outputs.get("names", [])):
        return jsonify({"available": False})

    names = [str(name) for name in outputs["names"]]
    values = np.asarray(outputs["values"], dtype=float).reshape(-1, len(names))
    count = values.shape[0]

    zone = zones.zone_data(result)

    # One row per zone, named like the zone map and the spectra chart.
    if zone is not None and len(zone["names"]) == count:
        return jsonify({
            "available": True,
            "kind": "zones",
            "names": names,
            "rows": zone["names"],
            "values": _json_numbers(values),
        })

    if count <= MAX_OUTPUT_ROWS:
        return jsonify({
            "available": True,
            "kind": "spectra",
            "names": names,
            "rows": [""] * count,
            "values": _json_numbers(values),
        })

    # An output missing for every spectrum just stays empty (NaN).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        summary = [
            np.nanmin(values, axis=0),
            np.nanmean(values, axis=0),
            np.nanmax(values, axis=0),
        ]

    return jsonify({
        "available": True,
        "kind": "summary",
        "names": names,
        "count": count,
        "values": _json_numbers(np.vstack(summary)),
    })


# ==========================================
# ZONES (zone map of a zone-based result - see zones.py)
# ==========================================

@bp.route("/zones")
def analysis_zones():

    return jsonify(zones.summary(state.CURRENT_RESULT))


@bp.route("/zones/labels.png")
def analysis_zone_labels():

    png = zones.label_map_png(state.CURRENT_RESULT)

    if png is None:
        return jsonify({"error": "No zones in the current result"}), 404

    return Response(png, mimetype="image/png")


@bp.route("/zones/rgb.jpg")
def analysis_zone_rgb():

    jpg = zones.rgb_jpeg(state.CURRENT_RESULT)

    if jpg is None:
        return jsonify({"error": "No zone photo in the current result"}), 404

    return Response(jpg, mimetype="image/jpeg")


# ==========================================
# SAVE CURRENT ANALYSIS
# ==========================================

@bp.route("/save", methods=["POST"])
def save_analysis():

    if state.CURRENT_RESULT is None:

        return jsonify({
            "error": "No analysis result"
        }), 400

    analysis = Analysis(
        reconstruction_dict=state.CURRENT_RESULT,
        plot_result=False
    )

    analysis.analysis_results = (
        copy.deepcopy(
            state.CURRENT_RESULT
        )
    )

    filepath = analysis.save_analysis_results()

    return jsonify({

        "success": True,

        "filename": filepath.name
    })


# ==========================================
# REFLECTANCE REFERENCE CAPTURE
# ==========================================
# Backs reflectance_normalization's reference_path parameter (see
# basic_treatments/reflectance_normalization.py): the GUI lets a user
# produce that file either by drawing a zone on a preview image, or by
# picking an existing measurement to use as a whole reference, without
# ever having to know a reference is "just a JSON file with a path".

@bp.route("/reference/preview")
def reference_preview():

    if state.CURRENT_RESULT is None:

        return jsonify({
            "error": "No reconstruction loaded"
        }), 400

    analysis = Analysis(
        reconstruction_dict=state.CURRENT_RESULT,
        plot_result=False
    )

    img = analysis.imaging_method.reference_preview_image(
        state.CURRENT_RESULT
    )

    if img is None:

        return jsonify({
            "error": (
                "This imaging method has no image a zone can be "
                "selected on; use a whole reference hypercube instead."
            )
        }), 404

    buf = io.BytesIO()

    Image.fromarray(
        np.asarray(img).astype(np.uint8)
    ).save(buf, format="PNG")

    buf.seek(0)

    return Response(
        buf.getvalue(),
        mimetype="image/png"
    )


@bp.route("/reference/zone", methods=["POST"])
def reference_zone():

    if state.CURRENT_RESULT is None:

        return jsonify({
            "error": "No reconstruction loaded"
        }), 400

    payload = request.json or {}

    try:

        x0 = int(payload["x0"])
        y0 = int(payload["y0"])
        x1 = int(payload["x1"])
        y1 = int(payload["y1"])

    except (KeyError, TypeError, ValueError):

        return jsonify({
            "error": "x0/y0/x1/y1 (integers) are required"
        }), 400

    analysis = Analysis(
        reconstruction_dict=state.CURRENT_RESULT,
        plot_result=False
    )

    try:

        spectrum, wavelengths = (
            analysis.imaging_method
            .reference_spectrum_zone(
                state.CURRENT_RESULT,
                x0, y0, x1, y1
            )
        )

    except ValueError as exc:

        return jsonify({"error": str(exc)}), 400

    filepath = save_reference_spectrum(
        spectrum,
        wavelengths
    )

    return jsonify({
        "reference_path": str(filepath)
    })


@bp.route("/reference/hypercube", methods=["POST"])
def reference_hypercube():

    filename = (request.json or {}).get("filename")

    save_path = get_measure_path()

    filepath = safe_path(save_path, filename)

    if filepath is None or not filepath.exists():

        return jsonify({
            "error": "File not found"
        }), 404

    try:

        reference_dict = onepix_utils.load_dict_json(
            filepath
        )

        imaging_method_name = (
            reference_dict.get("imaging_method_name")
            or reference_dict.get("metadata", {}).get("imaging_method_name")
        )

        if not imaging_method_name:

            return jsonify({
                "error": (
                    "No imaging_method_name found in that file; it "
                    "doesn't look like a reconstruction/analysis result."
                )
            }), 400

        bridge = ImagingMethodBridge(
            imaging_method_name,
            0,
            0
        )

        spectrum, wavelengths = (
            bridge.reference_spectrum_whole(
                reference_dict
            )
        )

    except Exception as exc:

        logger.exception(
            "Failed to build a reference from %s",
            filename
        )

        return jsonify({"error": str(exc)}), 400

    reference_filepath = save_reference_spectrum(
        spectrum,
        wavelengths
    )

    return jsonify({
        "reference_path": str(reference_filepath)
    })


# ==========================================
# SHARED STATE ACCESSOR
# ==========================================

def get_current_result():
    """Exposed for external analysis-blueprint plugins (e.g. the spectral
    indices plugin) that need the currently loaded result without being
    tied to a specific imaging method, unlike the Specific Analysis
    plugins below."""

    return state.CURRENT_RESULT


# ==========================================
# SPECIFIC IMAGING METHOD GUI
# ==========================================

@bp.route("/specific-target")
def specific_target():

    if state.CURRENT_RESULT is None:

        return jsonify({
            "error": "No reconstruction or analysis loaded"
        }), 400

    # imaging_method_name lives inside metadata on a current
    # reconstruction/analysis result; the top-level .get() keeps this
    # working on an older result saved before that.
    imaging_method = str(
        state.CURRENT_RESULT.get("imaging_method_name")
        or state.CURRENT_RESULT.get("metadata", {}).get("imaging_method_name", "")
    ).lower()

    if not imaging_method:

        return jsonify({
            "error": "No imaging_method_name found in current result"
        }), 400

    if imaging_method not in SPECIFIC_ANALYSIS_METHODS:

        return jsonify({
            "error": (
                f"No specific Flask interface registered "
                f"for imaging method '{imaging_method}'."
            ),
            "imaging_method_name": imaging_method
        }), 404

    return jsonify(
        {
            "imaging_method_name": imaging_method,
            "url": f"/analysis/method/{imaging_method}/"
        }
    )


def _result_for_specific_analysis():
    """Adapts state.CURRENT_RESULT for the external
    onepix-fis-common-function package's
    create_specific_analysis_blueprint() (FIS_common_flask.py's
    current_result() closure), which reads imaging_method_name only at
    the top level with no metadata fallback - that package isn't
    vendored in this repo, so it can't be changed to check metadata
    instead.

    Rather than storing imaging_method_name twice in every saved
    reconstruction/analysis file (it lives only in "metadata" - see
    Acquisition.build_metadata / Reconstruction.data_reconstruction /
    Analysis.data_analysis), the duplicate is synthesised here, on the
    fly, only for this one external integration point - a shallow copy,
    so the stored/saved result itself is never touched.
    """

    result = state.CURRENT_RESULT

    if result is None or "imaging_method_name" in result:
        return result

    imaging_method_name = result.get("metadata", {}).get("imaging_method_name")

    if imaging_method_name is None:
        return result

    return {**result, "imaging_method_name": imaging_method_name}


def register_imaging_method_specific_blueprints(app):
    """
    Register Flask GUIs provided by imaging method plugins.

    A plugin can expose a module named SpecificAnalysis
    with a function:

        create_blueprint(method_name, get_current_result, url_prefix)

    The blueprint will be mounted at:

        /analysis/method/<imaging_method>/
    """

    for imaging_method in ImagingMethodBridge.list_available_methods():

        method_key = imaging_method.lower()

        try:

            bridge = ImagingMethodBridge(
                method_key
            )

            module = bridge._import_submodule(
                "SpecificAnalysis"
            )

            create_blueprint = getattr(
                module,
                "create_blueprint"
            )

        except Exception as exc:

            logger.info(
                "No specific analysis GUI registered "
                "for %s: %s",
                method_key,
                exc
            )

            continue

        url_prefix = (
            f"/analysis/method/{method_key}"
        )

        app.register_blueprint(
            create_blueprint(
                method_name=method_key,
                get_current_result=_result_for_specific_analysis,
                url_prefix=url_prefix,
            )
        )

        SPECIFIC_ANALYSIS_METHODS.add(
            method_key
        )

        logger.info(
            "Registered specific analysis GUI for %s at %s",
            method_key,
            url_prefix
        )
