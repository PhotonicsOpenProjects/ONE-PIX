import importlib
import importlib.metadata
import logging

import numpy as np

from onepix.logging_config import root

logger = logging.getLogger(__name__)


class ImagingMethodBridge:
    """
    Bridge pour les méthodes d’imagerie ONE-PIX.

    Les méthodes d’imagerie doivent être installées
    comme des plugins Python déclarant une entry point
    dans 'onepix.imaging_methods'.
    """

    def __init__(
        self,
        imaging_method: str,
        height: int = 0,
        width: int = 0,
        plot_result: bool = False
    ):

        self.height = height
        self.width = width

        self.plot_result = plot_result

        self.imaging_method = (
            imaging_method.lower()
        )

        self.pattern_reduction = [4, 3]

        self.height = (
            height // self.pattern_reduction[0]
        )

        self.width = (
            width // self.pattern_reduction[1]
        )

        logger.info(
            f"🧩 Initialisation de la "
            f"méthode d’imagerie : "
            f"{self.imaging_method}"
        )

        # =====================================================
        # RESOLVE PLUGIN PACKAGE
        # =====================================================

        self.pkg_name = (
            self._resolve_plugin_package(
                self.imaging_method
            )
        )

        logger.info(
            f"📦 Plugin détecté : "
            f"{self.pkg_name}"
        )

    # =========================================================
    # PLUGIN RESOLUTION
    # =========================================================

    def _resolve_plugin_package(
        self,
        imaging_method: str
    ) -> str:
        """
        Resolve plugin package from entry points.
        Compatible Python 3.8 → 3.12.
        """

        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):

            eps_group = eps.select(
                group="onepix.imaging_methods"
            )

        else:

            eps_group = eps.get(
                "onepix.imaging_methods",
                []
            )

        for ep in eps_group:

            if (
                ep.name.lower()
                ==
                imaging_method.lower()
            ):

                return ep.value

        raise ImportError(
            f"❌ Aucun plugin trouvé pour "
            f"'{imaging_method}'."
        )

    # =========================================================
    # DYNAMIC IMPORT
    # =========================================================

    def _import_submodule(
        self,
        submodule: str
    ):

        module_path = (
            f"{self.pkg_name}.{submodule}"
        )

        try:

            return importlib.import_module(
                module_path
            )

        except ModuleNotFoundError as e:

            if e.name != module_path:

                raise ImportError(
                    f"❌ Dépendance '{e.name}' "
                    f"manquante pendant l'import de "
                    f"'{module_path}'."
                ) from e

            raise ImportError(
                f"❌ Sous-module "
                f"'{submodule}' introuvable "
                f"dans '{self.pkg_name}'."
            ) from e

    # =========================================================
    # ACQUISITION
    # =========================================================

    def creation_patterns(self):

        module = self._import_submodule(
            "PatternsCreation"
        )

        CreationPatterns = getattr(
            module,
            "CreationPatterns"
        )

        self.pattern_creation_method = (
            CreationPatterns(
                self.height,
                self.width
            )
        )

        self.pattern_creation_method.creation_patterns()

        self.config_path = (
            self.pattern_creation_method
            .config_path
        )

        self.acquisition_results = (
            self.pattern_creation_method
            .acquisition_results
        )

        logger.info(
            f"✅ Patterns créés avec "
            f"{self.imaging_method}"
        )

    # =========================================================
    # RECONSTRUCTION
    # =========================================================

    def reconstruction(
        self,
        acquisition_dict,
        plot_result=None
    ):

        module = self._import_submodule(
            "ImageReconstruction"
        )

        Reconstruction = getattr(
            module,
            "Reconstruction"
        )

        self.image_reconstruction_method = (
            Reconstruction(
                acquisition_dict
            )
        )

        self.reconstructed_image = (
            self.image_reconstruction_method
            .image_reconstruction()
        )

        if plot_result is None:

            plot_result = self.plot_result

        if plot_result:

            self.result_to_plot = (
                self.image_reconstruction_method
                .get_result_to_plot()
            )

        self.reconstruction_results = (
            self.image_reconstruction_method
            .reconstruction_results
        )

        logger.info(
            f"✅ Reconstruction terminée "
            f"({self.imaging_method})"
        )

    # =========================================================
    # ANALYSIS
    # =========================================================

    # Paquet utilisé en repli lorsqu'une méthode d'imagerie n'a pas
    # d'analyse dédiée (ex: Hadamard réutilise l'analyse FIS).
    _ANALYSIS_FALLBACK_PACKAGE = "fouriersplit"

    def _init_analysis_method(self):

        if hasattr(
            self,
            "image_analysis_method"
        ):

            return

        try:

            module = self._import_submodule(
                "ImageAnalysis"
            )

        except ImportError:

            logger.info(
                f"ℹ️ Pas d'analyse spécifique pour "
                f"'{self.pkg_name}', utilisation de "
                f"'{self._ANALYSIS_FALLBACK_PACKAGE}'."
            )

            module = importlib.import_module(
                f"{self._ANALYSIS_FALLBACK_PACKAGE}.ImageAnalysis"
            )

        Analysis = getattr(
            module,
            "Analysis"
        )

        self.image_analysis_method = (
            Analysis()
        )

    def result2spectraldata(
        self,
        reconstruction_dict
    ):

        self._init_analysis_method()

        return (
            self.image_analysis_method
            .result2spectraldata(
                reconstruction_dict
            )
        )

    def spectraldata2result(
        self,
        spectral_result,
        result_dict
    ):
        self._init_analysis_method()

        return (
            self.image_analysis_method
            .spectraldata2result(
                spectral_result,
                result_dict
            )
        )

    def create_result2plot(
        self,
        analysis_results
    ):

        self._init_analysis_method()

        return (
            self.image_analysis_method
            .create_result2plot(
                analysis_results
            )
        )

    # =========================================================
    # REFERENCE SPECTRA (reflectance normalization support)
    # =========================================================
    # Three optional hooks a method's Analysis class can override -
    # reference_preview_image() / reference_spectrum_zone() - when its
    # data isn't a per-pixel cube (e.g. HAS, which is cluster/mask
    # based - see has/ImageAnalysis.py). Methods that store a
    # "reconstructed_data" cube (FIS, Hadamard, DCT, ...) need neither
    # override: the fallbacks below already work directly off that
    # cube, so every such method gets zone/whole-hypercube reference
    # support for free.

    def reference_preview_image(self, result_dict):
        """A plain, undecorated RGB(-ish) array the GUI can let the user
        draw a selection rectangle on, pixel-for-pixel - unlike
        create_result2plot()'s output, which can bake in axes, legends
        or a side-by-side chart and so isn't safe to map click
        coordinates back onto. Returns None if this method has no
        image a zone can meaningfully be selected on."""

        self._init_analysis_method()

        override = getattr(
            self.image_analysis_method,
            "reference_preview_image",
            None
        )

        if override is not None:
            return override(result_dict)

        cube = result_dict.get("reconstructed_data")

        if cube is None:
            return None

        cube = np.asarray(cube)

        n_wl = cube.shape[-1]

        # Simple false-color composite (low/mid/high band) - just
        # enough to click a region on, not a radiometric rendering.
        band_idx = sorted(set(
            min(n_wl - 1, max(0, int(n_wl * frac)))
            for frac in (0.25, 0.5, 0.75)
        ))

        while len(band_idx) < 3:
            band_idx.append(band_idx[-1])

        rgb = cube[..., band_idx].astype(np.float64)

        spread = rgb.max() - rgb.min()

        if spread > 0:
            rgb = (rgb - rgb.min()) / spread

        return (rgb * 255).clip(0, 255).astype(np.uint8)

    def reference_spectrum_zone(self, result_dict, x0, y0, x1, y1):
        """Mean spectrum over a rectangular pixel region
        (x0 <= x < x1, y0 <= y < y1) of reference_preview_image()'s
        image, in that same image's pixel coordinates. Raises
        ValueError if the method has no per-pixel data to average
        (e.g. HAS falls back on its segmentation masks instead - see
        has/ImageAnalysis.py's override) or the zone is empty/invalid.

        Returns (spectrum, wavelengths) as plain numpy arrays.
        """

        self._init_analysis_method()

        override = getattr(
            self.image_analysis_method,
            "reference_spectrum_zone",
            None
        )

        if override is not None:
            return override(result_dict, x0, y0, x1, y1)

        cube = result_dict.get("reconstructed_data")

        if cube is None:
            raise ValueError(
                "This imaging method has no per-pixel data to select "
                "a zone from; use a whole reference hypercube instead."
            )

        cube = np.asarray(cube)
        wavelengths = np.asarray(result_dict["wavelengths"])

        height, width = cube.shape[0], cube.shape[1]

        x0, x1 = sorted((max(0, int(x0)), min(width, int(x1))))
        y0, y1 = sorted((max(0, int(y0)), min(height, int(y1))))

        region = cube[y0:y1, x0:x1, :]

        if region.size == 0:
            raise ValueError("The selected zone is empty.")

        spectrum = region.reshape(-1, region.shape[-1]).mean(axis=0)

        return spectrum, wavelengths

    def reference_spectrum_whole(self, result_dict):
        """Mean spectrum over an entire result - every spectrum
        result2spectraldata() would hand the processing pipeline,
        averaged into one. Works the same way for any imaging method
        (a flattened cube or a HAS-style series of cluster spectra)
        since it's built on that same generic conversion, so it needs
        no per-method override."""

        spectral_data = self.result2spectraldata(result_dict)

        values = np.asarray(spectral_data.values)
        wavelengths = np.asarray(spectral_data.wavelengths)

        return values.mean(axis=0), wavelengths

    # =========================================================
    # DISCOVERY
    # =========================================================

    @staticmethod
    def list_available_methods() -> list[str]:
        """
        Liste les plugins installés.
        Compatible Python 3.8 → 3.12.
        """

        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):

            eps_group = eps.select(
                group="onepix.imaging_methods"
            )

        else:

            eps_group = eps.get(
                "onepix.imaging_methods",
                []
            )

        return sorted(
            [
                ep.name
                for ep in eps_group
            ]
        )
