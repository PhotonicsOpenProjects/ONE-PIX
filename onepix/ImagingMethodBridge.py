import importlib
import importlib.metadata
import logging

from onepix.logging_config import root
logger = logging.getLogger(__name__)


class ImagingMethodBridge:
    """
    Bridge pour les méthodes d’imagerie ONE-PIX (version plugin-only).
    Les méthodes d’imagerie doivent être installées comme des paquets Python,
    déclarant une entry point dans 'onepix.imaging_methods'.
    """

    def __init__(self, imaging_method: str, height: int = 0, width: int = 0, plot_result: bool = False):
        self.height = height
        self.width = width
        self.plot_result = plot_result
        self.imaging_method = imaging_method.lower()
        self.pattern_reduction = [4, 3]
        self.height = height // self.pattern_reduction[0]
        self.width = width // self.pattern_reduction[1]

        logger.info(f"🧩 Initialisation de la méthode d’imagerie : {self.imaging_method}")

        # Résolution du package associé via entry points
        self.pkg_name = self._resolve_plugin_package(self.imaging_method)
        logger.info(f"📦 Plugin détecté : {self.pkg_name}")

    # -------------------------------------------------------------------------
    # 🔍 Résolution du plugin
    # -------------------------------------------------------------------------
    def _resolve_plugin_package(self, imaging_method: str) -> str:
        """
        Trouve le module Python associé à la méthode d’imagerie via les entry points.
        Compatible Python 3.8 → 3.12.
        """
        eps = importlib.metadata.entry_points()

        # Compatibilité selon version Python
        if hasattr(eps, "select"):  # Python 3.10+
            eps_group = eps.select(group="onepix.imaging_methods")
        else:  # Python 3.8 / 3.9
            eps_group = eps.get("onepix.imaging_methods", [])

        for ep in eps_group:
            if ep.name.lower() == imaging_method.lower():
                return ep.value

        raise ImportError(
            f"❌ Aucun plugin trouvé pour la méthode '{imaging_method}'. "
            "Vérifie qu’il est bien installé et déclare une entry point dans 'onepix.imaging_methods'."
        )

    # -------------------------------------------------------------------------
    # 📦 Import dynamique des sous-modules
    # -------------------------------------------------------------------------
    def _import_submodule(self, submodule: str):
        """
        Importe dynamiquement un sous-module du plugin (PatternsCreation, ImageReconstruction, ImageAnalysis).
        """
        module_path = f"{self.pkg_name}.{submodule}"
        try:
            return importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            raise ImportError(f"❌ Le sous-module '{submodule}' est introuvable dans '{self.pkg_name}'.") from e

    # -------------------------------------------------------------------------
    # 🧠 Méthodes publiques
    # -------------------------------------------------------------------------
    def creation_patterns(self):
        module = self._import_submodule("PatternsCreation")
        CreationPatterns = getattr(module, "CreationPatterns")
        self.pattern_creation_method = CreationPatterns(self.height, self.width)
        self.pattern_creation_method.creation_patterns()
        self.acquisition_results = self.pattern_creation_method.acquisition_results
        logger.info(f"✅ Patterns créés avec {self.imaging_method}")

    def reconstruction(self, acquisition_dict, plot_result=None):
        module = self._import_submodule("ImageReconstruction")
        Reconstruction = getattr(module, "Reconstruction")
        self.image_reconstruction_method = Reconstruction(acquisition_dict)
        self.reconstructed_image = self.image_reconstruction_method.image_reconstruction()

        # ✅ On utilise l’argument s’il est passé, sinon self.plot_result par défaut
        if plot_result is None:
            plot_result = self.plot_result

        if plot_result:
            self.result_to_plot = self.image_reconstruction_method.get_result_to_plot()

        self.reconstruction_results = self.image_reconstruction_method.reconstruction_results
        logger.info(f"✅ Reconstruction terminée ({self.imaging_method})")

    def analysis(self, data_path=None):
        module = self._import_submodule("ImageAnalysis")
        Analysis = getattr(module, "Analysis")
        self.image_analysis_method = Analysis(data_path)
        logger.info(f"✅ Analyse effectuée avec {self.imaging_method}")

    # -------------------------------------------------------------------------
    # 🧭 Découverte des plugins installés
    # -------------------------------------------------------------------------
    @staticmethod
    def list_available_methods() -> list[str]:
        """
        Liste toutes les méthodes d’imagerie installées et déclarées dans 'onepix.imaging_methods'.
        Compatible Python 3.8 → 3.12.
        """
        eps = importlib.metadata.entry_points()
        if hasattr(eps, "select"):  # Python 3.10+
            eps_group = eps.select(group="onepix.imaging_methods")
        else:  # Python 3.8 / 3.9
            eps_group = eps.get("onepix.imaging_methods", [])
        return sorted([ep.name for ep in eps_group])
