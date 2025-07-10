import os
import json
from flask import Flask
from flask_socketio import SocketIO, emit
from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from onepix.Analysis import Analysis
import numpy as np 

# Chemin vers le dossier de configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_DIR = os.path.join(BASE_DIR, '..', '..', "conf")

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


@socketio.on('connect')
def on_connect():
    print("Client connecté")


@socketio.on('instruction')
def on_instruction(data):
    print("Instruction reçue :", data)
    action = data.get("action")

    if action == "mesure":

        acq = Acquisition()
        acq.thread_acquisition(time_warning=False)
        rec =Reconstruction(acq)
        rec.data_reconstruction()
        ana=Analysis(rec)
        rgb_img=ana.get_rgb_image(rec.imaging_method.reconstructed_image,rec.wavelengths)
        print("rgb reconstructed",np.shape(rgb_img))
        emit('mesure', {'hypercube': rec.imaging_method.reconstructed_image.tolist(),"wavelengths" :rec.wavelengths.tolist(),"rgb_img":rgb_img.tolist()})

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
    socketio.run(app, host='0.0.0.0', port=5000)
