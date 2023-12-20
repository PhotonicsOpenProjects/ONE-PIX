import importlib
import numpy as np
import os

class ImagingMethodBridge:
    """
    """
    
    def __init__(self,imaging_method):
		# Concrete spectrum implementation dynamic instanciation
        try:
            className=imaging_method
            module=importlib.import_module('plugins.imaging_methods.'+className)

            pattern_creation_classObj = getattr(module,'PatternsCreation')
            image_reconstruction_classObj = getattr(module, 'ImageReconstruction')
            image_analysis_classObj = getattr(module, 'ImageAnalysis')

            self.pattern_creation_method = pattern_creation_classObj()
            self.image_reconstruction_method = image_reconstruction_classObj()
            self.image_analysis_method = image_analysis_classObj()

        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + imaging_method + "\" implementation has not been found.")

    def creation_pattern(self):
        self.pattern_creation_method.creation_pattern()
        self.patterns=self.pattern_creation_method.patterns
        self.patterns_order=self.pattern_creation_method.patterns_order


    def reconstruction(self):
        self.image_reconstruction_method.image_reconstruction(self.patterns.self.patterns_order)
        self.reconstruct_image=self.image_reconstruction_method.reconstruct_image
    
    