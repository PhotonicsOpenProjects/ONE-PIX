import os
import importlib.util


import logging
from onepix.logging_config import root  
logger = logging.getLogger(__name__)

class ImagingMethodBridge:
    def __init__(self, imaging_method=None,height=0, width=0):
        # Define width and height pixels numbers with a reduction coefficient to save memory
        self.pattern_reduction = [4, 3]
        self.height = height // self.pattern_reduction[0]
        self.width = width // self.pattern_reduction[1]
        self.imaging_method = imaging_method
        logging.info(f'{self.imaging_method} imaging method is init')

    def creation_patterns(self):
        try:
            module_path = f"plugins.imaging_methods.{self.imaging_method}.PatternsCreation"
            module = importlib.import_module(module_path)

            class_obj = getattr(module, "CreationPatterns")
            self.pattern_creation_method = class_obj(self.height, self.width)
            self.pattern_creation_method.creation_patterns()
            self.acquisition_results = self.pattern_creation_method.acquisition_results
            logging.info(f'patterns of {self.imaging_method} are created ')
        except Exception as e:
            raise Exception(
                f'Concrete bridge "{self.imaging_method}" had an error during create patterns: {e}'
            )

    def reconstruction(self, spectra,wavelengths, pattern_order,imaging_method_param,plot_result=False):
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
                spectra,wavelengths, pattern_order,imaging_method_param
            )
            self.reconstructed_image = (
                self.image_reconstruction_method.image_reconstruction()
            )
            if plot_result:
                logging.info('test to create plot result')
                self.result_to_plot=self.image_reconstruction_method.get_result_to_plot()

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
