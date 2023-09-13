import sys
import os
import screeninfo
import numpy as np

sys.path.append(os.path.abspath('../'))
from AcquisitionConfig import *

class OPTest:
    def __init__(self,json_path) -> None:
       self.json_path=json_path
    
    def is_picam_running():
        if is_raspberry():
            try:
                import picamera
                camera=picamera.PiCamera()
                test=True
            except:
                test=False
            
        return test

    def is_spectrometer_running():
        test=False
        try:
            config=OPConfig(self.json_path)
            config.spec_lib.spec_open()
            config.spec_lib.set_integration_time_ms()
            wl=config.spec_lib.get_wavelengths()
            spectrum=config.spec_lib.get_intensities()
            if np.logicaland(wl !=[],spectrum !=[]): test=True
        except:
            test=False
        config.spec_lib.spec_close()
        return test
    
    def is_projector_running():
        try:
            proj_shape=screeninfo.get_monitors()[1]
            test=True
        except IndexError:
            test=False
        return test
    

