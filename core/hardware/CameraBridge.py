import importlib
from src.spectrometer_bridges.AbstractBridge import AbstractBridge
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
    
    def __init__(self,spectro_name,integration_time_ms,wl_lim):
		# Concrete spectrum implementation dynamic instanciation
       
 		
    def camera_open(self):
       
    
    def get_image(self):
     
    
    