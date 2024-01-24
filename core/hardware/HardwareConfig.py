
import json  
import os
import io
import numpy as np
from core.hardware.SpectrometerBridge import *
from core.hardware.CameraBridge import *
from core.hardware.Projection import *
import screeninfo

screenWidth = screeninfo.get_monitors()[0].width
try:
    proj_shape=screeninfo.get_monitors()[1]
    
except IndexError:
    print('Please use a projector to use ONE-PIX')
    #sys.exit()

class Hardware :

    def __init__(self): 
        self.root_path=os.getcwd()
        conf_path=f'..{os.sep}..{os.sep}conf'
        self.harware_config_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),conf_path , 'hardware_config.json')
        with open(self.harware_config_path) as f:
            hardware_dict = json.load(f)
       

        self.name_spectro = hardware_dict["name_spectro"]
        self.name_camera=hardware_dict["name_camera"]

        self.acquisition_parameter_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),conf_path ,'acquisition_parameters.json')
        
        with open(self.acquisition_parameter_path) as f:
            param_dict = json.load(f)

        self.integration_time_ms =hardware_dict["integration_time_ms"]    
        self.repetition=hardware_dict["spectro_scans2avg"]
        self.height = hardware_dict['height']
        self.width = hardware_dict["width"]
        self.proj_position=np.array(hardware_dict["proj_position"])
        self.spatial_res = param_dict['spatial_res']
        self.spectra = []
        self.res=[]
        self.normalised_datacube=[]
        self.spectro_flag=False

        self.wl_lim=param_dict["wl_lim"]
        
        
        # Displaying infos
        self.interp_method=None
        self.periode_pattern=int(self.repetition*self.integration_time_ms)
        if self.periode_pattern<60 :self.periode_pattern=60

        self.spectrometer= SpectrometerBridge(self.name_spectro,self.integration_time_ms,self.wl_lim,self.repetition)
        self.camera=CameraBridge(self.name_camera)
        self.projection=Projection(self.height,self.width,self.periode_pattern,self.proj_position)

    def is_raspberrypi(self):
        """
        is_raspberrypi return a boolean to determine if the current OS is a raspberrry

        """
        try:
            with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
                if 'raspberry pi' in m.read().lower(): return True
        except Exception: pass
        return False
    
    def hardware_initialisation(self):

        # Spectrometer connection
        if self.spectrometer.DeviceName=='':
            self.spectrometer.spec_open()
        
        self.spectrometer.set_integration_time()
        self.spectrometer.get_wavelengths() 
        
        # Camera connection
        self.camera.camera_open()
        
        #self.projection.reshape_patterns(self,patterns)
    
    







