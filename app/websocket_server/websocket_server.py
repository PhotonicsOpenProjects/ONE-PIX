import os
import json
import secrets
import threading
from flask import Flask
from flask_socketio import SocketIO, emit, ConnectionRefusedError
from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from onepix.progress import progress as acquisition_progress
from onepix.progress import AcquisitionCancelled
import numpy as np

# Chemin vers le dossier de configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_DIR = os.path.join(BASE_DIR, '..', '..', "conf")

app = Flask(__name__)

# CORS is a browser-enforced defense - it doesn't stop this client
# (socketio.Client(), Python) or curl, only cross-origin requests made
# by a browser page. Left restrictable via ONEPIX_WS_CORS_ORIGINS for
# anyone who does expose this to a browser context; no origins allowed
# by default.
_cors_origins_env = os.environ.get("ONEPIX_WS_CORS_ORIGINS", "")
CORS_ORIGINS = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else []
)

socketio = SocketIO(app, cors_allowed_origins=CORS_ORIGINS)

# Shared secret required to open a connection (see on_connect below). No
# fallback to "no auth required" - if it isn't set, every connection is
# refused rather than silently accepted, and that's logged loudly at
# startup so it's impossible to miss on a fresh deployment.
WS_TOKEN = os.environ.get("ONEPIX_WS_TOKEN")

if not WS_TOKEN:
    print(
        "WARNING: ONEPIX_WS_TOKEN is not set - this WebSocket server "
        "will refuse every connection. Set it to a shared secret "
        "(e.g. `export ONEPIX_WS_TOKEN=$(python -c "
        "'import secrets; print(secrets.token_urlsafe(32))')`) and "
        "configure OnePixClient with the same value."
    )

# Serializes access to Acquisition/Reconstruction across connections -
# two concurrent 'mesure' instructions would otherwise race on the same
# physical camera/spectrometer/projector.
_measure_lock = threading.Lock()


def _to_list(value):
    """Best-effort conversion to a plain (JSON-serializable) list.
    reconstruction/analysis results mix numpy arrays and plain lists
    depending on where they came from (live hardware vs. a JSON file),
    so .tolist() alone isn't safe to call unconditionally."""
    if value is None:
        return None
    return value.tolist() if hasattr(value, "tolist") else list(value)


@socketio.on('connect')
def on_connect(auth):
    if not WS_TOKEN or not auth or not secrets.compare_digest(
        str(auth.get("token", "")), WS_TOKEN
    ):
        print("Connexion refusée : jeton absent ou invalide")
        raise ConnectionRefusedError("authentication required")

    print("Client connecté (authentifié)")


@socketio.on('instruction')
def on_instruction(data):
    print("Instruction reçue :", data)
    action = data.get("action")

    if action == "mesure":

        if not _measure_lock.acquire(blocking=False):
            emit("erreur", {
                "message": "Une acquisition est déjà en cours, réessayez plus tard."
            })
            return

        try:
            acq = Acquisition()
            acq.thread_acquisition()

            rec = Reconstruction(acq.acquisition_results, plot_result=True)
            rec.data_reconstruction()

            hypercube = rec.imaging_method.reconstructed_image
            wavelengths = rec.wavelengths
            rgb_img = rec.reconstruction_results.get("result2plot")

            print("rgb reconstructed", np.shape(rgb_img) if rgb_img is not None else None)

            emit('mesure', {
                'hypercube': _to_list(hypercube),
                'wavelengths': _to_list(wavelengths),
                'rgb_img': _to_list(rgb_img),
            })
        except AcquisitionCancelled as e:
            print("Mesure annulée :", e)
            emit("mesure_annulee", {"message": str(e)})
        except Exception as e:
            print("Erreur mesure :", e)
            emit("erreur", {"message": f"Erreur pendant la mesure : {e}"})
        finally:
            _measure_lock.release()

    elif action == "annuler_mesure":
        cancelled = acquisition_progress.request_cancel()
        emit("annulation", {"cancelled": cancelled})

    elif action == "get_param":
        key = data.get("key")
        if not key:
            emit("erreur", {"message": "Clé manquante pour lecture"})
            return

        value = None
        found_in = None
        for filename in os.listdir(CONF_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(CONF_DIR, filename)
            try:
                with open(path, "r") as f:
                    config = json.load(f)
                if key in config:
                    value = config[key]
                    found_in = filename
                    break
            except Exception as e:
                print(f"Erreur lecture {filename} :", e)
                continue

        if found_in:
            emit("param_data", {"key": key, "value": value, "file": found_in})
        else:
            emit("erreur", {"message": f"Clé '{key}' introuvable dans les fichiers de config"})

    elif action == "update_param":
        key = data.get("key")
        raw_value = data.get("value")

        if key is None or raw_value is None:
            emit("erreur", {"message": "Clé ou valeur manquante"})
            return

        updated = False
        for filename in os.listdir(CONF_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(CONF_DIR, filename)

            try:
                with open(path, "r") as f:
                    config = json.load(f)
            except Exception as e:
                print(f"Erreur lecture JSON {filename} :", e)
                continue

            if key in config:
                current_value = config[key]
                target_type = type(current_value)

                try:
                    if target_type == int:
                        new_value = int(raw_value)
                    elif target_type == float:
                        new_value = float(raw_value)
                    elif target_type == bool:
                        new_value = str(raw_value).lower() in ("true", "1", "yes")
                    elif target_type == list or target_type == dict:
                        new_value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
                    else:
                        new_value = str(raw_value)
                except Exception as e:
                    emit("erreur", {
                        "message": f"Erreur de conversion pour '{key}': {e}"
                    })
                    return

                config[key] = new_value

                try:
                    with open(path, "w") as f:
                        json.dump(config, f, indent=2)
                except Exception as e:
                    emit("erreur", {"message": f"Erreur lors de l'écriture du fichier {filename}: {e}"})
                    return

                emit("config_updated", {
                    "file": filename,
                    "key": key,
                    "new_value": new_value
                })
                updated = True
                break

        if not updated:
            emit("erreur", {"message": f"Clé '{key}' introuvable dans les fichiers de config."})

    else:
        emit('erreur', {'message': f"Instruction inconnue : {action}"})
        print(f"Instruction inconnue reçue : {action}")


@socketio.on('disconnect')
def on_disconnect():
    print("Client déconnecté")


if __name__ == '__main__':
    # 0.0.0.0 by default: this server is designed to be controlled from
    # other devices on the local network (same tradeoff as the main
    # Flask app's SEC-1 fix) - safe now that on_connect() requires
    # ONEPIX_WS_TOKEN. Set ONEPIX_WS_HOST=127.0.0.1 to restrict further.
    host = os.environ.get("ONEPIX_WS_HOST", "0.0.0.0")
    socketio.run(app, host=host, port=5000)
