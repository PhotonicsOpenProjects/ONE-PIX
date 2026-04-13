from flask import render_template, Response, request, redirect, url_for, send_file
from . import bp, controllers as ctl

import io
import json
import orjson
import logging
import numpy as np
import matplotlib.pyplot as plt
import time

from pathlib import Path
from importlib.metadata import entry_points

from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction

logger = logging.getLogger(__name__)


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
            "name_camera": get_entrypoints("onepix.cameras"),
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


@bp.route("/addon")
def addon_page():
    return render_template(
        "settings_page.html",
        title="Addon settings",
        category="addon",
        data=ctl.addon_settings()
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
    return redirect(url_for(f"acquisition.{category}_page"))


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


# ----------------------------
# RUN ACQUISITION
# ----------------------------
@bp.route("/run")
def run_acquisition():

    # 1. Acquisition
    acq = Acquisition()
    acq.init_measure()
    acq.thread_acquisition()

    # 2. Reconstruction
    rec = Reconstruction(acq.acquisition_results, plot_result=True)
    rec.data_reconstruction()

    # 3. Backup serveur
    save_path = Path(__file__).resolve().parent.parent / "measure"
    save_path.mkdir(exist_ok=True)

    filename = f"reconstruction_{time.strftime('%d_%m_%Y_%H-%M-%S')}.json"
    filepath = save_path / filename

    with open(filepath, "wb") as f:
        f.write(
            orjson.dumps(
                rec.reconstruction_results,
                option=orjson.OPT_SERIALIZE_NUMPY,
                default=json_default
            )
        )

    logger.info(f"Saved: {filepath}")

    # 4. Plot image
    img = rec.reconstruction_results.get("result2plot")

    if img is None:
        return "No image to display", 500

    fig, ax = plt.subplots()
    ax.imshow(img, cmap="viridis")
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    return Response(buf.getvalue(), mimetype="image/png")


# ----------------------------
# LIST + DOWNLOAD MEASURES
# ----------------------------
@bp.route("/download_measure")
def download_measure():

    save_path = Path(__file__).resolve().parent.parent / "measure"
    files = sorted(save_path.glob("reconstruction_*.json"), reverse=True)
    filenames = [f.name for f in files]

    return render_template("download_measure.html", files=filenames)


@bp.route("/download_measure/<filename>")
def download_measure_file(filename):

    save_path = Path(__file__).resolve().parent.parent / "measure"
    filepath = save_path / filename

    if not filepath.exists():
        return "File not found", 404

    return send_file(
        filepath,
        mimetype="application/json",
        as_attachment=True,
        attachment_filename=filename
    )


# ----------------------------
# LOAD MEASURE
# ----------------------------
@bp.route("/load_measure", methods=["POST"])
def load_measure():

    file = request.files.get("file")
    if not file:
        return "No file", 400

    data = json.load(file)

    rec = Reconstruction(data, plot_result=False)
    rec.data_reconstruction()

    img = rec.reconstruction_results.get("result2plot")

    if img is None:
        return "No plottable data", 400

    fig, ax = plt.subplots()
    ax.imshow(img, cmap="viridis")
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    return Response(buf.getvalue(), mimetype="image/png")