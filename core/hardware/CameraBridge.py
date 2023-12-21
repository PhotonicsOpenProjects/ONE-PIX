import importlib
from plugins.camera.AbstractBridge import AbstractBridge
import numpy as np

class CameraBridge:
    """
     Allows to build a generic bridge based on a concrete one. Concrete 
     bridge provides correct implementation regarding spectrometer model
     use. The generic bridge is an abstract layer that wrap concrete implementation.
    
     :param str spectro_name:
    		Spectrometer concrete bridge implementation:
    		
     :param float integration_time_ms:
    		spectrometer integration time in milliseconds.
    """
    
    def __init__(self,camera_name):
		# Concrete spectrum implementation dynamic instanciation1
        try:
            className=camera_name+'Bridge'
            module=importlib.import_module('plugins.camera.'+className)
            classObj = getattr(module, className)
            #self.decorator = classObj(integration_time_ms)            
        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + camera_name + "\" implementation has not been found.")
        return
       
 		
    def camera_open(self):
        return
       
    
    def get_image(self):
        return
     
    
    