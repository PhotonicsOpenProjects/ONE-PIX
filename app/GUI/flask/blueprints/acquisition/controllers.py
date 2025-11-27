import os
import json
from pathlib import Path
from onepix.Acquisition import Acquisition


# ----------------------------
#   CONFIG PATHS
# ----------------------------
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATHS_FILE = os.path.join(BASE_DIR, "config_paths.json")


def _load_config_paths() -> dict:
    """Charge config_paths.json : mapping category -> fichier JSON."""
    if not os.path.exists(CONFIG_PATHS_FILE):
        return {}
    with open(CONFIG_PATHS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_config_path(category: str) -> str:
    """Retourne le chemin complet du JSON correspondant à la catégorie."""
    paths = _load_config_paths()
    rel_path = paths.get(category)

    if not rel_path:
        return None

    return os.path.abspath(os.path.join(BASE_DIR, rel_path))


def load_settings(category: str) -> dict:
    """Ouvre le JSON de configuration d'une catégorie (hardware / software)."""
    path = get_config_path(category)

    if not path or not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
#   TYPE CASTING AUTOMATIQUE
# ----------------------------
def _cast_like(value: str, reference):
    """Convertit une valeur string selon le type de la référence JSON."""
    if isinstance(reference, bool):
        return value.lower() in ("true", "1", "yes")

    if isinstance(reference, int):
        try:
            return int(value)
        except ValueError:
            return reference

    if isinstance(reference, float):
        try:
            return float(value)
        except ValueError:
            return reference

    if isinstance(reference, (list, dict)):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return reference

    return value


def save_settings(category: str, data: dict):
    """Sauvegarde hardware/software dans leur JSON correspondant."""
    path = get_config_path(category)
    if not path:
        raise FileNotFoundError(f"Aucun chemin configuré pour {category}")

    old = load_settings(category)
    new = {}

    for k, v in data.items():
        if k in old:
            new[k] = _cast_like(v, old[k])
        else:
            try:
                new[k] = json.loads(v)
            except:
                new[k] = v

    with open(path, "w", encoding="utf-8") as f:
        json.dump(new, f, indent=2, ensure_ascii=False)


# ----------------------------
#   WRAPPERS PRATIQUES
# ----------------------------
def hardware_settings():
    return load_settings("hardware")


def software_settings():
    return load_settings("software")


# ----------------------------
#   ADDON SETTINGS (🔥 NOUVEAU)
# ----------------------------
def addon_settings():
    """
    Charge dynamiquement la configuration de l’addon
    basé sur la méthode d’imagerie choisie dans software_settings.json.
    """
    # 1. Lire software_settings pour récupérer la méthode choisie
    sw = software_settings()
    method = sw.get("imaging_method_name")

    if not method:
        print("⚠️ No imaging method selected in software settings")
        return {}

    # 2. Créer une mini acquisition pour obtenir le chemin du JSON du plugin
    try:
        acq = Acquisition(imaging_method_name=method)
        acq.init_measure()
    except Exception as e:
        print(f"❌ Cannot initialize addon {method}: {e}")
        return {}

    # 3. Récupérer le path du JSON dans le plugin
    path = acq.imaging_method.config_path

    if not path or not os.path.exists(path):
        print(f"⚠️ Addon config not found at {path}")
        return {}

    # 4. Charger le JSON du plugin
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
