import os
import pytest
import numpy as np
from onepix.Reconstruction import Reconstruction
import json

def test_reconstruction_full_integration():
    """
    ✅ Test d’intégration complet de la classe Reconstruction :
    - Charge un dictionnaire d'acquisition depuis tests/test_params/acquisition_results_for_test.json
    - Instancie la vraie classe
    - Lance data_reconstruction()
    - Vérifie la présence et le contenu des clés :
        * 'wavelengths'
        * 'reconstructed_data'
        * 'result2plot'
    """

    # 📂 Chemin vers le JSON de test
    base_dir = os.path.dirname(__file__)
    test_params_dir = os.path.join(base_dir, "test_params")
    acquisition_json = os.path.join(test_params_dir, "acquisition_results_for_test.json")

    # 🧭 Vérifie que le fichier existe
    assert os.path.exists(acquisition_json), f"⚠️ Fichier manquant : {acquisition_json}"

    # 📖 Charge le contenu du fichier
    with open(acquisition_json, "r", encoding="utf-8") as f:
        acquisition_dict = json.load(f)

    # 🚀 Instanciation réelle
    rec = Reconstruction(acquisition_dict=acquisition_dict, plot_result=True)

    # ✅ Vérifie l’instanciation
    assert isinstance(rec, Reconstruction)
    assert isinstance(rec.acquisition_dict, dict)
    assert "imaging_method_name" in rec.acquisition_dict, "⚠️ 'imaging_method_name' manquant"
    assert "wavelengths" in rec.acquisition_dict, "⚠️ 'wavelengths' manquant"

    # 🚀 Lancement reconstruction
    rec.data_reconstruction()

    # ✅ Vérifications globales
    rr = rec.reconstruction_results
    assert isinstance(rr, dict), "⚠️ reconstruction_results doit être un dictionnaire"
    assert rr, "⚠️ reconstruction_results est vide"

    # ✅ Vérifie les 3 clés essentielles
    for key in ["wavelengths", "reconstructed_data", "result2plot"]:
        assert key in rr, f"⚠️ Clé '{key}' absente"
        val = rr[key]
        if isinstance(val, (list, dict, np.ndarray)):
            assert len(val) > 0, f"⚠️ '{key}' vide"
        else:
            assert val is not None, f"⚠️ '{key}' est None"

    # ✅ Vérifie cohérence des données
    wl = rr["wavelengths"]
    data = rr["reconstructed_data"]

    assert isinstance(wl, (list, np.ndarray)), "⚠️ 'wavelengths' doit être liste/array"
    assert len(wl) > 0, "⚠️ 'wavelengths' vide"
    assert isinstance(data, np.ndarray), "⚠️ 'reconstructed_data' doit être numpy array"
    assert data.size > 0, "⚠️ 'reconstructed_data' vide"
