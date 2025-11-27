from flask import render_template, Response, request, redirect, url_for,jsonify, send_file
from . import bp, controllers as ctl  
import io
import matplotlib.pyplot as plt
import numpy as np
from onepix.Acquisition import *
from onepix.Reconstruction import *
from onepix.Analysis import *

latest_results = None


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


@bp.route("/")
def acquisition_page():
    return render_template("acquisition.html")


@bp.route("/hardware")
def hardware_page():
    return render_template("settings_page.html",
                           title="Hardware settings",
                           category="hardware",
                           data=ctl.hardware_settings())

@bp.route("/software")
def software_page():
    return render_template("settings_page.html",
                           title="Software settings",
                           category="software",
                           data=ctl.software_settings())

@bp.route("/imaging")
def imaging_page():
    return render_template("settings_page.html",
                           title="Imaging settings",
                           category="imaging",
                           data=ctl.imaging_method_settings())


@bp.route("/save/<category>", methods=["POST"])
def save_settings(category):
    # Récupère les nouvelles valeurs depuis le formulaire
    new_data = dict(request.form)

    # Écrase le JSON avec les nouvelles valeurs
    ctl.save_settings(category, new_data)

    # Redirige vers la page settings correspondante pour voir le résultat
    return redirect(url_for(f"acquisition.{category}_page"))

@bp.route("/run")
def run_acquisition():
    global latest_results

    acq = Acquisition()
    acq.init_measure()
    acq.thread_acquisition()

    rec = Reconstruction(acq.acquisition_results, plot_result=True)
    rec.data_reconstruction()

    # 🔥 On stocke ici les résultats pour SAVE
    latest_results = rec.reconstruction_results

    # --- Génération image PNG ---
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(rec.imaging_method.result_to_plot, cmap="viridis")
    ax.set_title("Résultat acquisition")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    return Response(buf.getvalue(), mimetype="image/png")

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
        download_name="measure.json"
    )
