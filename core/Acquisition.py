"""
@author:PhotonicsOpenProjects
Modified and traducted by Leo Brechet on Wed Jul 19 18:32:47 2023

"""
from core.hardware.HardwareConfig import *
from core.ImagingMethodBridge import *
import io
import os
import json
import time
import threading
import numpy as np
from datetime import date
import platform
import screeninfo
from tkinter import *
from tkinter.messagebox import askquestion
import PIL
import PIL.ImageTk



class Acquisition:
    """ 
    Class OPConfig is used to set up ONE-PIX acquisitions
    
    :param str spectro_name:
   		Spectrometer concrete bridge implementation:
   		
    :param float integration_time_ms:
   		spectrometer integration time in milliseconds.
           
    """

    def __init__(self):

        self.software_config_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), f'..{os.sep}conf', 'software_config.json')
        ## get software configuration
        f = open(self.software_config_path)
        software_dict = json.load(f)
        f.close()

        self.acquisition_config_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), f'..{os.sep}conf', 'acquisition_parameters.json')
        ## get software configuration
        f = open(self.acquisition_config_path)
        acquisition_dict = json.load(f)
        f.close()

        self.imaging_method_name=software_dict["imaging_method"]
        self.spatial_res=acquisition_dict["spatial_res"]
        self.hardware=Hardware()
        self.imaging_method=ImagingMethodBridge(self.imaging_method_name)

    def init_measure(self):
        """
        This function allows to initialize the display window and the patterns to be displayed before the starts of threads.
    
    
        Parameters
        ----------
        config : class
            OPConfig class object.
    
        Returns
        -------
        config : class
        * actualised OPConfig class object.
        * self.pattern_lib.decorator.sequence : sequence of patterns
        """
        self.imaging_method.creation_patterns(self.spatial_res)
        self.nb_patterns = len(self.imaging_method.pattern_order)
        self.hardware.hardware_initialisation()
        self.spectra=np.zeros((self.nb_patterns,len(self.wavelengths)),dtype=np.float32)

     
        
    def thread_acquisition(self, path=None, time_warning=True):
        """
        This funtion allows to run in parallel the projection of a sequence of 
        patterns and spectrometers' measurements in free running mode. 
        The result is measured hyperspectral chronograms need to be processed to 
        extract means spectrums for each patterns.
    
    
        Parameters
        ----------
        config : class
            OPConfig class object.
    
        Returns
        -------
        config : class
        * actualised OPConfig class object.
        * spectra : (array of floats) 2D array of spectra stored in chronological order.
        * wavelengths : (array of floats) 1D wavelengths sampled by the spectrometer.
    
        """
        est_duration=round((self.pattern_lib.nb_patterns*(self.periode_pattern+self.rep*(self.integration_time_ms+2))+2)/(60*1000),2)
        ans='no'
        if time_warning :
            ans=askquestion(message=f"Estimated acquisition duration : {est_duration} min ")
        if np.logical_or(ans=='yes',time_warning==False):
            begin_acq = time.time()
            self.init_measure()
            #Threads initialisation
            event=threading.Event()
            patterns_thread = threading.Thread(target=self.hardware.projection.thread_projection,args=(event,))
            spectrometer_thread = threading.Thread(target=self.hardware.spectrometer.thread_singlepixel_measure,args=(event,))
            # Start both display and measure threads
            patterns_thread.start()
            spectrometer_thread.start()
            patterns_thread.join()
            spectrometer_thread.join()
            self.spectra=self.hardware.spectrometer.spectra
            self.duration = time.time()-begin_acq
            #self.save_acquisition_envi(path)
            
        else:
            cv2.destroyAllWindows()
            pass

    def save_raw_data(self):
        return 