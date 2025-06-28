import socketio

# Création du client
sio = socketio.Client()

# Étape 1 : à la connexion, on modifie le paramètre
@sio.event
def connect():
    print("Connecté au serveur")

    # Envoie d'abord la mise à jour du paramètre
    sio.emit('instruction', {
        'action': 'update_param',
        'key': "imaging_method",
        'value': 'FourierSplit'
    })

# Réponse à la mise à jour de config
@sio.on('config_updated')
def on_config_updated(data):
    print("Configuration mise à jour :", data)

    # Étape 2 : lancer la mesure après mise à jour
    sio.emit('instruction', {
        'action': 'mesure'
    })

# Étape 3 : réception de la mesure
@sio.on('mesure')
def on_mesure(data):
    print("Mesure reçue :", data)
    sio.disconnect()

@sio.event
def disconnect():
    print("Déconnecté du serveur")

# Connexion au serveur Flask-SocketIO
sio.connect('http://localhost:5000')  # ou l'adresse IP du serveur
sio.wait()
