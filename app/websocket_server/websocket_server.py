import os
import json
from flask import Flask
from flask_socketio import SocketIO, emit
from onepix.Acquisition import Acquisition

# Dossier contenant les fichiers de config

# Dossier de config — chemin absolu basé sur le script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_DIR = os.path.join(BASE_DIR,'..','..',"conf")


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


@socketio.on('connect')
def on_connect():
    print("Client connecté")


@socketio.on('instruction')
def on_instruction(data):
    print("Instruction reçue :", data)
    action = data.get("action")

    # Lancer une mesure
    if action == "mesure":
        acq = Acquisition()
        acq.thread_acquisition(time_warning=False)
        emit('mesure', {'raw_data': acq.spectra.tolist()})

    # Mise à jour transparente d'une clé dans les fichiers JSON

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
        new_value = data.get("value")

        if not key:
            emit("erreur", {"message": "Clé manquante"})
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
                config[key] = new_value
                with open(path, "w") as f:
                    json.dump(config, f, indent=2)
                emit("config_updated", {
                    "file": filename,
                    "key": key,
                    "new_value": new_value
                })
                updated = True
                break

        if not updated:
            emit("erreur", {"message": f"Clé '{key}' introuvable dans les fichiers de config."})

    # Instruction non reconnue
    else:
        emit('erreur', {'message': f"Instruction inconnue : {action}"})
        print(f"Instruction inconnue reçue : {action}")


@socketio.on('disconnect')
def on_disconnect():
    print("Client déconnecté")


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
