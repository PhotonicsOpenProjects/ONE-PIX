from core.hardware.HardwareConfig import *
from core.ImagingMethodBridge import *
import cv2
import os
import json
import time
import threading
import numpy as np
from tkinter import *
from tkinter.messagebox import askquestion
from datetime import date


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
        with open(self.software_config_path) as f:
            software_dict = json.load(f)

        self.acquisition_config_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), f'..{os.sep}conf', 'acquisition_parameters.json')
        
        ## get software configuration
        with open(self.acquisition_config_path) as f:
            acquisition_dict = json.load(f)

        self.imaging_method_name=software_dict["imaging_method"]
        self.spatial_res=acquisition_dict["spatial_res"]
        self.width=acquisition_dict["width"]
        self.height=acquisition_dict["height"]
        self.imaging_method=ImagingMethodBridge(self.imaging_method_name,self.spatial_res,self.height,self.width)
        self.hardware=Hardware()
        

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
        #self.wavelengths=self.hardware.spectrometer.wavelengths
        self.imaging_method.creation_patterns()
        self.nb_patterns = len(self.imaging_method.patterns_order)
        self.hardware.hardware_initialisation()
        self.spectra=np.zeros((self.nb_patterns,len(self.hardware.spectrometer.wavelengths)),dtype=np.float32)

     
        
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
        self.init_measure()
        est_duration=round((self.nb_patterns*(self.hardware.periode_pattern+self.hardware.repetition*(self.hardware.integration_time_ms+2))+2)/(60*1000),2)
        ans='no'
        if time_warning :
            ans=askquestion(message=f"Estimated acquisition duration : {est_duration} min ")
        if np.logical_or(ans=='yes',time_warning==False):
            begin_acq = time.time()
            #Threads initialisation
            event=threading.Event()
            patterns_thread = threading.Thread(target=self.hardware.projection.thread_projection,args=(event,self.imaging_method.patterns,self.imaging_method.patterns_order,self.imaging_method.pattern_creation_method.interp_method))
            spectrometer_thread = threading.Thread(target=self.hardware.spectrometer.thread_singlepixel_measure,args=(event,self.spectra))
            print("ok")
            # Start both display and measure threads
            patterns_thread.start()
            spectrometer_thread.start()
            patterns_thread.join()
            spectrometer_thread.join()

            self.spectra=self.hardware.spectrometer.spectra
            self.camera_image=self.hardware.camera.get_image() 
            self.duration = time.time()-begin_acq
            self.create_acquisition_header()
            
            
        else:
            cv2.destroyAllWindows()
            pass

    def create_acquisition_header(self):
        fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time    
        # Header
        self.title_param = f"raw_acquisition_parameters_{fdate}_{actual_time}.txt"
        self.header = f"ONE-PIX_raw_acquisition_{fdate}_{actual_time}"+"\n"\
            + "--------------------------------------------------------"+"\n"\
            + "\n"\
            + f"Imaging method: {self.imaging_method_name}"+"\n"\
            + "Acquisition duration: %f s" % self.duration+"\n" \
            + f"Spectrometer {self.hardware.name_spectro} : {self.hardware.spectrometer.DeviceName}"+"\n"\
            + f"Camera: {self.hardware.name_camera}" +"\n"\
            + "Number of projected patterns: %d" % self.nb_patterns+"\n" \
            + "Height of pattern window: %d pixels" % self.height+"\n" \
            + "Width of pattern window: %d pixels" % self.width+"\n" \
            + "Number of spectral measures per pattern: %d  " %self.hardware.repetition+"\n" \
            + "Integration time: %d ms" % self.hardware.spectrometer.integration_time_ms+"\n" 
    
    
    def save_raw_data(self,path=None):
        self.imaging_method.pattern_creation_method.save_raw_data(self)