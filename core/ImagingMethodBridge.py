import importlib
import numpy as np
import os
import sys
# directory reach
current_directory = os.path.dirname(os.path.realpath(__file__))

# setting path
#sys.path.append(os.path.dirname(current_directory))

class ImagingMethodBridge:
    """
    """
    
    def __init__(self,imaging_method):
        
        try:
            #Import patterns creation, reconstruction and analysis modules specifics to the chosen imaging method
            patterns_module=importlib.import_module(f'plugins.imaging_methods.{imaging_method}.'+'PatternsCreation')
            reconstruction_module=importlib.import_module(f'plugins.imaging_methods.{imaging_method}.'+'ImageReconstruction')
            analysis_module=importlib.import_module(f'plugins.imaging_methods.{imaging_method}.'+'ImageAnalysis')
            #Get the class the specific modules
            self.pattern_creation_classObj = getattr(patterns_module,'CreationPatterns')
            self.image_reconstruction_classObj = getattr(reconstruction_module, 'Reconstruction')
            self.image_analysis_classObj = getattr(analysis_module, 'Analysis')

        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + imaging_method + "\" implementation has not been found.")

    def creation_patterns(self,spatial_res):
        self.pattern_creation_method = self.pattern_creation_classObj(spatial_res)
        self.pattern_creation_method.creation_patterns()
        self.patterns=self.pattern_creation_method.patterns
        self.patterns_order=self.pattern_creation_method.patterns_order


    def reconstruction(self,spectra,pattern_order):
        self.image_reconstruction_method = self.image_reconstruction_classObj(spectra,pattern_order)
        self.reconstructed_image=self.image_reconstruction_method.reconstruct_image()
    
    def analysis(self):
        self.image_analysis_method = self.image_analysis_classObj(self.reconstructed_image)

    