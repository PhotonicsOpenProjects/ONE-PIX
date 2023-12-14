import importlib
import numpy as np

class imaging_methodBridge:
    """
    """
    
    def __init__(self,imaging_method):
		# Concrete spectrum implementation dynamic instanciation
        try:
            module='plugins.imaging_method_bridges'
            className=imaging_method+'Bridge'
            module=importlib.import_module('plugins.spectrometer_bridges.'+className)
            classObj = getattr(module, className)
            self.decorator = classObj()
        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + imaging_method + "\" implementation has not been found.")

    def creation_pattern(self):
        self.decorator.creation_pattern()
        self.patterns=self.decorator.patterns
        self.patterns_order=self.decorator.patterns


    def reconstruction(self):
        self.decorator.image_reconstruction()
        self.reconstruct_image=self.decorator.reconstruct_image 
    
    