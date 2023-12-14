
import json  
from  plugins.spectrometer.SpectrometerBridge  import *
from  plugins.camera.cameraBridge  import *
from core.hardware.Projection  import *

class Hardware :

    def __init__(self): 

        self.harware_config_path="./conf/hardware_config.json"
        f = open(self.harware_config_path)
        hardware_dict = json.load(f)
        f.close()

        self.name_spectro = hardware_dict["name_spectro"]
        self.name_camera=hardware_dict["name_camera"]

        self.acquisition_parameter_path="./conf/acquisition_parameter.json"

        f = open(self.acquisition_parameter_path)
        param_dict = json.load(f)
        f.close()

        integration_time_ms =param_dict["integration_time_ms"]
       
        self.repetition=param_dict["spectro_scans2avg"]
        self.height = param_dict['height']
        self.width = param_dict["width"]
        self.spatial_res = param_dict['spatial_res']
        
        self.spectra = []
        self.res=[]
        self.normalised_datacube=[]
        self.wavelengths = []
        self.spectro_flag=False

        integration_time_ms =param_dict["integration_time_ms"]
        wl_lim=param_dict["wl_lim"]
        self.spectrometer= SpectrometerBridge(self.name_spectro,integration_time_ms,wl_lim)

        self.camera=CameraBridge()
        self.projection=Projection()

    def is_raspberrypi():
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
        self.spectrometer.wavelengths = self.spectrometer.get_wavelengths()
        

        projection.reshape_patterns(self,patterns)
    
    







