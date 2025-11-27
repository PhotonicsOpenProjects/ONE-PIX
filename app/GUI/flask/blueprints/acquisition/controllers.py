import os
import json
from onepix.Acquisition import *

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATHS_FILE = os.path.join(BASE_DIR, "config_paths.json")




def _load_config_paths() -> dict:
    """Charge le mapping category -> chemin JSON"""
    if not os.path.exists(CONFIG_PATHS_FILE):
        return {}
    with open(CONFIG_PATHS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_config_path(category: str) -> str:
    """Retourne le chemin absolu du fichier config pour une catégorie"""
    paths = _load_config_paths()
    print(paths)
    rel_path = paths.get(category)
    if not rel_path:
        return None
    return os.path.abspath(os.path.join(BASE_DIR, rel_path))

def load_settings(category: str) -> dict:
    """Charge la config JSON pour une catégorie donnée"""
    path = get_config_path(category)
    print(path)
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
import json

def _cast_like(value: str, reference):
    """Cast value en gardant le même type que reference (int, float, bool, list, dict)"""
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
    path = get_config_path(category)
    if not path:
        raise FileNotFoundError(f"Aucun chemin configuré pour {category}")

    old_data = load_settings(category)

    new_data = {}
    for k, v in data.items():
        if k in old_data:
            new_data[k] = _cast_like(v, old_data[k])
        else:
            # si pas dans l'ancien JSON, on tente une auto-détection
            try:
                new_data[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                new_data[k] = v

    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)



# Wrappers pratiques (utilisés par tes routes)
def hardware_settings():
    print("try hardware setting")
    return load_settings("hardware")

def software_settings():
    return load_settings("software")

def imaging_method_settings():
    # 1. Charger le software_settings
    sw = software_settings()
    method = sw.get("imaging_method_name")

    if not method:
        print("⚠️ No imaging method selected in software settings")
        return {}

    # 2. Créer un mini Acquisition uniquement pour accéder au path
    acq = Acquisition(imaging_method_name=method)
    acq.init_measure()

    # 3. Récupérer le chemin du JSON de l’addon
    path = acq.imaging_method.config_path

    if not path or not os.path.exists(path):
        print(f"⚠️ Config path not found for imaging method {method}")
        return {}

    # 4. Charger le JSON du plugin
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
