import os
import json
import logging
from pathlib import Path
from onepix.ImagingMethodBridge import ImagingMethodBridge
from onepix.utils import write_json_atomic

import gui_plugins
from i18n import t

logger = logging.getLogger(__name__)


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

    # Merged into what is there: a request that carries only some of the keys must not erase the
    # others (the hardware cannot start without its configuration).
    new = dict(old)

    for k, v in data.items():
        if k in old:
            new[k] = _cast_like(v, old[k])
        else:
            try:
                new[k] = json.loads(v)
            except (ValueError, TypeError):
                new[k] = v

    write_json_atomic(path, new, indent=2, ensure_ascii=False)


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
def imaging_config_path(method):
    """Path of an imaging method's own config file, or None.

    Read from its CreationPatterns, only built - running it
    (creation_patterns()) would project and photograph the scene, and
    the full acquisition setup this used to go through also opened the
    spectrometer and left it busy for the next acquisition.
    """
    bridge = ImagingMethodBridge(method)
    module = bridge._import_submodule("PatternsCreation")
    patterns = module.CreationPatterns(bridge.height, bridge.width)
    return getattr(patterns, "config_path", None)


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

    # 2. Chemin du JSON du plugin, sans toucher au matériel
    try:
        path = imaging_config_path(method)
    except Exception as e:
        print(f"❌ Cannot initialize addon {method}: {e}")
        return {}

    if not path or not os.path.exists(path):
        print(f"⚠️ Addon config not found at {path}")
        return {}

    # 3. Charger le JSON du plugin
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



# ----------------------------
#   ACQUISITION OVERVIEW (main page summary + pre-flight checks)
# ----------------------------
def acquisition_overview() -> dict:
    """What the next acquisition will use, plus known problems that
    would make it fail, for the main Acquisition page.

    Reads the config files directly - it runs on every load of the
    main page, so it must not initialize any hardware.

    imaging_summary and warnings come from the selected imaging
    method's own plugin (gui_plugins.method_overview()): only it knows
    what its setup looks like and what it needs. Each warning is
    {"message": text, "fix": "hardware" | "imaging"}, the settings page
    that fixes it.
    """
    sw = software_settings()
    hw = hardware_settings()

    imaging_summary, warnings = gui_plugins.method_overview(
        sw.get("imaging_method_name"), sw, hw, t
    )

    return {
        "imaging_method": sw.get("imaging_method_name"),
        "integration_time_ms": sw.get("integration_time_ms"),
        "scans": sw.get("spectro_scans2avg"),
        "spectrometer": hw.get("name_spectro"),
        "camera": hw.get("name_camera"),
        "wl_lim": hw.get("wl_lim"),
        "imaging_summary": imaging_summary,
        "warnings": warnings,
    }
