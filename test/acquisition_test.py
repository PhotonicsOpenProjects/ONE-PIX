import os
import pytest
from onepix.Acquisition import Acquisition
import numpy as np 

def test_acquisition_init_with_test_json():
    """
    ✅ Teste l’instanciation complète d’Acquisition avec les JSON de test.
    """

    # 📂 Chemins vers les JSON de test
    base_dir = os.path.dirname(__file__)
    test_params_dir = os.path.join(base_dir, "test_params")

    hardware_json = os.path.join(test_params_dir, "hardware_config.json")
    acquisition_json = os.path.join(test_params_dir, "acquisition_parameters.json")

    # 🚀 Création de l’instance avec les chemins
    acq = Acquisition(
        hardware_json_path=hardware_json,
        acquisition_json_path=acquisition_json
    )

    # ✅ Vérifications de base
    assert isinstance(acq, Acquisition)
    assert acq.hardware_dict != {}
    assert acq.acquisition_results != {}

    # Vérifie la présence de clés essentielles
    assert "width" in acq.hardware_dict, "⚠️ clé 'width' manquante dans hardware_config.json"
    assert "height" in acq.hardware_dict, "⚠️ clé 'height' manquante dans hardware_config.json"
    assert "imaging_method_name" in acq.acquisition_results, "⚠️ clé 'imaging_method_name' manquante dans acquisition_parameters.json"

    # L’état initial doit être propre
    assert acq.is_init is False


def test_acquisition_init_measure():
    """
    ✅ Teste que init_measure() s’exécute sans erreur avec la vraie structure.
    (⚠️ suppose que ImagingMethodBridge et Hardware sont fonctionnels en mode stub)
    """

    base_dir = os.path.dirname(__file__)
    test_params_dir = os.path.join(base_dir, "test_params")

    hardware_json = os.path.join(test_params_dir, "hardware_config.json")
    acquisition_json = os.path.join(test_params_dir, "acquisition_parameters.json")

    acq = Acquisition(
        hardware_json_path=hardware_json,
        acquisition_json_path=acquisition_json
    )

    # 🚀 Lancement de l'initialisation de mesure
    acq.init_measure()

    # ✅ L’état doit être initialisé
    assert acq.is_init is True

    # ✅ Les attributs clés doivent être définis
    assert hasattr(acq, "spectra")
    assert hasattr(acq, "nb_patterns")
    assert hasattr(acq, "est_duration")

    # ✅ Spectra doit être un tableau numpy cohérent
    import numpy as np
    assert isinstance(acq.spectra, np.ndarray)
    assert acq.spectra.size > 0

    # ✅ Vérifie la durée estimée
    assert isinstance(acq.est_duration, float)
    assert acq.est_duration > 0

def test_thread_acquisition_full():
    """
    ✅ Test d'intégration complet :
    - Charge les JSON de test dans test/test_params/
    - Lance un thread_acquisition()
    - Vérifie la présence et le contenu des clés essentielles :
        * imaging_method.acquisition_results["patterns"]
        * imaging_method.acquisition_results["patterns_order"]
        * acquisition_results["spectra"]
        * acquisition_results["wavelengths"]
    """

    # 📂 Chemins vers les fichiers JSON de test
    base_dir = os.path.dirname(__file__)
    test_params_dir = os.path.join(base_dir, "test_params")

    hardware_json = os.path.join(test_params_dir, "hardware_config.json")
    acquisition_json = os.path.join(test_params_dir, "acquisition_parameters.json")

    # 🚀 Création de l’instance avec les fichiers JSON de test
    acq = Acquisition(
        hardware_json_path=hardware_json,
        acquisition_json_path=acquisition_json
    )

    # 🧪 Lancement du processus d’acquisition complet
    acq.thread_acquisition()

    # ✅ Vérifications globales
    assert hasattr(acq, "spectra"), "⚠️ 'spectra' n’a pas été créé"
    assert hasattr(acq, "duration"), "⚠️ 'duration' n’a pas été défini"
    assert hasattr(acq, "acquisition_results"), "⚠️ 'acquisition_results' manquant"

    # ✅ Vérifie la présence des clés essentielles
    im_results = acq.imaging_method.acquisition_results
    acq_results = acq.acquisition_results

    for key in ["patterns", "patterns_order"]:
        assert key in im_results, f"⚠️ Clé '{key}' absente dans imaging_method.acquisition_results"

    for key in ["spectra", "wavelengths"]:
        assert key in acq_results, f"⚠️ Clé '{key}' absente dans acquisition_results"

    # ✅ Vérifie le contenu
    patterns = im_results["patterns"]
    patterns_order = im_results["patterns_order"]
    spectra = acq_results["spectra"]
    wavelengths = acq_results["wavelengths"]

    # ---- patterns ----
    assert isinstance(patterns, (np.ndarray, list)), "'patterns' doit être un tableau ou une liste"
    if isinstance(patterns, np.ndarray):
        assert patterns.ndim in (2, 3), "⚠️ 'patterns' devrait être 2D ou 3D"
        assert patterns.size > 0, "⚠️ 'patterns' ne doit pas être vide"
    elif isinstance(patterns, list):
        assert len(patterns) > 0, "⚠️ 'patterns' ne doit pas être vide"

   # ---- patterns_order ----
    assert isinstance(patterns_order, (list, np.ndarray)), "'patterns_order' doit être une liste ou un array"
    assert len(patterns_order) > 0, "⚠️ 'patterns_order' vide"
    assert all(isinstance(i, (str, int, np.integer)) for i in patterns_order), \
        "⚠️ 'patterns_order' doit contenir uniquement des chaînes ou des entiers"


    # ---- spectra ----
    assert isinstance(spectra, np.ndarray), "'spectra' doit être un numpy array"
    assert spectra.ndim == 2, "⚠️ 'spectra' doit être 2D (nb_patterns x nb_wavelengths)"
    assert spectra.shape[0] == len(patterns_order), "⚠️ incohérence entre nb de patterns et nb de spectres"
    assert spectra.shape[1] == len(wavelengths), "⚠️ incohérence entre nb de longueurs d'onde et nb de colonnes de spectres"
    assert not np.isnan(spectra).any(), "⚠️ 'spectra' contient des NaN"

    # ---- wavelengths ----
    assert isinstance(wavelengths, (list, np.ndarray)), "'wavelengths' doit être une liste ou un array"
    assert len(wavelengths) > 0, "⚠️ 'wavelengths' vide"

    # ✅ Vérifie que la durée est bien mesurée
    assert isinstance(acq.duration, float), "⚠️ 'duration' doit être un float"
    assert acq.duration > 0, "⚠️ 'duration' doit être positive"

    # ✅ Vérifie la présence d’un header
    assert hasattr(acq, "header"), "⚠️ 'header' non créé"
    assert "Imaging method" in acq.header, "⚠️ 'header' semble incomplet"