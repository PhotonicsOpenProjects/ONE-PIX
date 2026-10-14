import importlib
import importlib.metadata
import logging

logger = logging.getLogger(__name__)


class CameraBridge:
    """
    Generic ONE-PIX camera bridge (plugin-based).

    Each concrete camera must be installed as a Python package
    declaring an entry-point in 'onepix.cameras'.
    """

    def __init__(self, camera_name):
        try:
            self.camera_name = camera_name

            logger.info(f"🎥 Initialisation de la caméra : {camera_name}")

            # 🔍 Resolve plugin package via entry-point
            self.pkg_name = self._resolve_plugin_package(camera_name)
            logger.info(f"📦 Plugin caméra détecté : {self.pkg_name}")

            # 📦 Import plugin module
            module = importlib.import_module(self.pkg_name)

            # ------------------------------------------------------------------
            # 🔎 Recherche intelligente du nom de classe
            #    (comme SpectrometerBridge)
            # ------------------------------------------------------------------
            class_candidates = [
                f"{camera_name}Bridge",
                f"{camera_name.capitalize()}Bridge",
                camera_name,
                camera_name.capitalize(),
                f"{camera_name}Camera",
                f"{camera_name.capitalize()}Camera",
                # Ajout CamelCase explicite pour les plugins OnePix
                "StubCamera",
                "CameraStub",
            ]

            cam_class = None
            for cname in class_candidates:
                if hasattr(module, cname):
                    cam_class = getattr(module, cname)
                    logger.info(f"Classe détectée pour la caméra : {cname}")
                    break

            if cam_class is None:
                raise ImportError(
                    f"Aucune classe compatible trouvée dans '{self.pkg_name}'. "
                    f"Recherchées : {class_candidates}"
                )

            # ✔ Instanciation du plugin
            self.camera = cam_class()
            logger.info(f"{self.camera_name} camera plugin initialisé")

        except Exception as e:
            raise Exception(f'Camera bridge "{camera_name}" could not be loaded: {e}')

    # -------------------------------------------------------------------------
    # 🔍 Resolve plugin package from entry-points
    # -------------------------------------------------------------------------
    def _resolve_plugin_package(self, camera_name: str) -> str:
        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):  # Python ≥ 3.10
            eps_group = eps.select(group="onepix.cameras")
        else:
            eps_group = eps.get("onepix.cameras", [])

        for ep in eps_group:
            if ep.name.lower() == camera_name.lower():
                return ep.value

        raise ImportError(
            f"❌ Aucun plugin caméra trouvé pour '{camera_name}'. "
            "Vérifie qu’il est bien installé et qu'il déclare une entry-point dans 'onepix.cameras'."
        )

    # -------------------------------------------------------------------------
    # 🎥 API standard ONE-PIX Camera
    # -------------------------------------------------------------------------
    def camera_open(self):
        self.camera.init_camera()
        logger.info(f"{self.camera_name} camera is open")

    def get_image(self, tag=None, save_path=None):
        self.camera_open()
        img = self.camera.image_capture(tag, save_path)
        self.close_camera()
        return img

    def close_camera(self):
        self.camera.close()
        logger.info(f"{self.camera_name} camera is closed")
