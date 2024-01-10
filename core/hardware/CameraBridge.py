import importlib
import sys
import os
sys.path.append(f'..{os.sep}..{os.sep}')

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
            module_name=f'plugins.camera.{camera_name}.'
            module=importlib.import_module(module_name+className)
            classObj = getattr(module, className)
            self.camera = classObj()            
        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + camera_name + "\" implementation has not been found.")
        return
       
 		
    def camera_open(self):
        self.camera.init_camera()

    
    def get_image(self,tag=None,save_path=None):
        self.image=self.camera.image_capture(tag,save_path)
        
    
        
     
    
    