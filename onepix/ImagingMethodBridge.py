import os
import importlib.util

class ImagingMethodBridge:
    def __init__(self, imaging_method=None, spatial_res=0, height=0, width=0):
        # Define width and height pixels numbers with a reduction coefficient to save memory
        self.pattern_reduction = [4, 3]
        self.height = height // self.pattern_reduction[0]
        self.width = width // self.pattern_reduction[1]
        self.spatial_res = spatial_res
        self.imaging_method = imaging_method

    def creation_patterns(self):
        try:
            module_path = f"plugins.imaging_methods.{self.imaging_method}.PatternsCreation"
            module = importlib.import_module(module_path)

            class_obj = getattr(module, "CreationPatterns")
            self.pattern_creation_method = class_obj(
                self.spatial_res, self.height, self.width
            )
            self.patterns = self.pattern_creation_method.creation_patterns()
            self.patterns_order = self.pattern_creation_method.patterns_order

        except Exception as e:
            raise Exception(
                f'Concrete bridge "{self.imaging_method}" implementation has not been found: {e}'
            )

    def reconstruction(self, spectra, pattern_order):
        try:
            # Import reconstruction module specific to the chosen imaging method
            reconstruction_module = importlib.import_module(
                f"plugins.imaging_methods.{self.imaging_method}."
                + "ImageReconstruction"
            )
            self.image_reconstruction_classObj = getattr(
                reconstruction_module, "Reconstruction"
            )
            self.image_reconstruction_method = self.image_reconstruction_classObj(
                spectra, pattern_order
            )
            self.reconstructed_image = (
                self.image_reconstruction_method.image_reconstruction()
            )
        except ModuleNotFoundError:
            raise Exception(
                'Concrete bridge "'
                + self.imaging_method
                + '" implementation has not been found.'
            )

    def analysis(self, data_path=None):
        try:
            # Import analysis modules specifics to the chosen imaging method
            analysis_module = importlib.import_module(
                f"plugins.imaging_methods.{self.imaging_method}." + "ImageAnalysis"
            )
            self.image_analysis_classObj = getattr(analysis_module, "Analysis")
            self.image_analysis_method = self.image_analysis_classObj(data_path)
        except ModuleNotFoundError:
            raise Exception(
                'Concrete bridge "'
                + self.imaging_method
                + '" implementation has not been found.'
            )
