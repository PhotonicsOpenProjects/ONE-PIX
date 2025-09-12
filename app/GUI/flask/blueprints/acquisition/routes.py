from flask import render_template, Response, request, redirect, url_for
from . import bp, controllers as ctl  
import io
import matplotlib.pyplot as plt
import numpy as np
from onepix.Acquisition import *
from onepix.Reconstruction import *
from onepix.Analysis import *



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

    acq=Acquisition()
    
    acq.init_measure()
    acq.thread_acquisition()
    rec=Reconstruction(acq,plot_result=True)
    rec.data_reconstruction()
    """Génère une mosaïque aléatoire au clic sur 'Run acquisition'"""
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(rec.imaging_method.result_to_plot, cmap="viridis")

    ax.set_title("Résultat acquisition")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    return Response(buf.getvalue(), mimetype="image/png")
