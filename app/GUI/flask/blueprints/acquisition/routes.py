from flask import render_template, Response, request, redirect, url_for, jsonify, send_file
from . import bp, controllers as ctl
import io
import matplotlib.pyplot as plt
import numpy as np
from onepix.Acquisition import *
from onepix.Reconstruction import *
from onepix.Analysis import *
from pathlib import Path
import json
import orjson
from importlib.metadata import entry_points

latest_results = None


# 🔥 GENERIC PLUGIN LOADER
def get_entrypoints(group_name):
    """Generic loader for plugins."""
    try:
        eps = entry_points()

        if hasattr(eps, "select"):
            eps = eps.select(group=group_name)
        else:
            eps = eps.get(group_name, [])

        return [ep.name for ep in eps]

    except Exception as e:
        print(f"⚠️ Error loading {group_name}: {e}")
        return []


# --- JSON FIXER ---
def json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.int_)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float_)):
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


# --- PAGES SETTINGS --- #
@bp.route("/")
def acquisition_page():
    return render_template("acquisition.html")


@bp.route("/hardware")
def hardware_page():
    return render_template(
        "settings_page.html",
        title="Hardware settings",
        category="hardware",
        data=ctl.hardware_settings(),
        plugins={
            "name_spectro": get_entrypoints("onepix.spectrometers"),
            "name_camera": get_entrypoints("onepix.cameras"),  # 🔥 AJOUT CAMERA
        }
    )


@bp.route("/software")
def software_page():
    return render_template(
        "settings_page.html",
        title="Software settings",
        category="software",
        data=ctl.software_settings(),
        plugins={
            "imaging_method_name": get_entrypoints("onepix.imaging_methods")
        }
    )


# 🔥 Nouvelle page addon
@bp.route("/addon")
def addon_page():
    return render_template(
        "settings_page.html",
        title="Addon settings",
        category="addon",
        data=ctl.addon_settings()
    )


# ⚠ Redirection
@bp.route("/imaging")
def imaging_page():
    return redirect(url_for("acquisition.addon_page"))


# --- SAVE HARDWARE / SOFTWARE --- #
@bp.route("/save/<category>", methods=["POST"])
def save_settings(category):
    new_data = dict(request.form)
    ctl.save_settings(category, new_data)
    return redirect(url_for(f"acquisition.{category}_page"))


# --- SAVE ADDON --- #
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

    return redirect(url_for("acquisition.addon_page"))


# --- RUN ACQUISITION --- #
@bp.route("/run")
def run_acquisition():
    global latest_results

    acq = Acquisition()
    acq.init_measure()
    acq.thread_acquisition()

    rec = Reconstruction(acq.acquisition_results, plot_result=True)
    rec.data_reconstruction()

    latest_results = rec.reconstruction_results

    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(rec.imaging_method.result_to_plot, cmap="viridis")
    ax.set_title("Résultat acquisition")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    return Response(buf.getvalue(), mimetype="image/png")


# --- SAVE MEASURE JSON --- #
@bp.route("/save_measure")
def save_measure():
    global latest_results

    if latest_results is None:
        return "No acquisition done yet", 400

    json_bytes = orjson.dumps(
        latest_results,
        option=orjson.OPT_SERIALIZE_NUMPY,
        default=json_default
    )

    return send_file(
        io.BytesIO(json_bytes),
        mimetype="application/json",
        as_attachment=True,
        attachment_filename="measure.json"
    )