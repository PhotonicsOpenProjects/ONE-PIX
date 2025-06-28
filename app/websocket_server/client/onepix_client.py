import socketio
import threading

class OnePixClient:
    def __init__(self, server_url="http://localhost:5000", timeout=10):
        self.server_url = server_url
        self.timeout = timeout
        self.sio = socketio.Client()
        self._result = None
        self._error = None
        self._wait_event = threading.Event()

        @self.sio.event
        def connect():
            print("✅ Connecté au serveur")

        @self.sio.event
        def disconnect():
            print("🔌 Déconnecté du serveur")

        @self.sio.on('config_updated')
        def on_config_updated(data):
            self._result = data
            self._wait_event.set()

        @self.sio.on('config_data')
        def on_config_data(data):
            self._result = data
            self._wait_event.set()

        @self.sio.on('mesure')
        def on_mesure(data):
            self._result = data
            self._wait_event.set()

        @self.sio.on('erreur')
        def on_erreur(data):
            self._error = data
            self._wait_event.set()

    def connect(self):
        self.sio.connect(self.server_url)

    def disconnect(self):
        self.sio.disconnect()

    def change_param(self, key, value):
        self._reset()
        self.sio.emit('instruction', {
            "action": "update_param",
            "key": key,
            "value": value
        })
        self._wait_event.wait(self.timeout)
        return self._get_response()

    def read_param(self, key):
        self._reset()
        self.sio.emit('instruction', {
            "action": "get_config",  # ou 'get_param' si tu implémentes
            "name": "acquisition_parameters"
        })
        self._wait_event.wait(self.timeout)
        if self._result and "config" in self._result:
            return self._result["config"].get(key)
        return None

    def run_measure(self):
        self._reset()
        self.sio.emit('instruction', {"action": "mesure"})
        self._wait_event.wait(self.timeout)
        return self._get_response()

    def _reset(self):
        self._result = None
        self._error = None
        self._wait_event.clear()

    def _get_response(self):
        if self._error:
            raise RuntimeError(f"Erreur serveur : {self._error}")
        return self._result
