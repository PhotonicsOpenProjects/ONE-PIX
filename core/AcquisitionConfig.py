"""
@author:PhotonicsOpenProjects
Modified and traducted by Leo Brechet on Wed Jul 19 18:32:47 2023

"""
import cv2
import io
import os
import sys
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
import customtkinter as ctk
from src.SpectrometerBridge import SpectrometerBridge 
from src.PatternMethods import PatternMethodSelection
from src.DatacubeReconstructions import *
from src.datacube_analyse import *
from src.coregistration_lib import *


def is_raspberrypi():
    """
    is_raspberrypi return a boolean to determine if the current OS is a raspberrry

    """
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False

screenWidth = screeninfo.get_monitors()[0].width
try:
    proj_shape=screeninfo.get_monitors()[1]
except IndexError:
    print('Please use a projector to use ONE-PIX')
    #sys.exit()

class OPConfig:
    """ 
    Class OPConfig is used to set up ONE-PIX acquisitions
    
    :param str spectro_name:
   		Spectrometer concrete bridge implementation:
   		
    :param float integration_time_ms:
   		spectrometer integration time in milliseconds.
           
    """

    def __init__(self,json_path,img=None,nb_patterns=0):
        # Initialize the OPConfig object
        self.json_path=json_path
        #Get info from acquisition_param_ONE-PIX.json
        f = open(json_path)
        acqui_dict = json.load(f)
        f.close()

        # Spectrometer infos
        self.name_spectro = acqui_dict["name_spectro"]
        self.integration_time_ms =acqui_dict["integration_time_ms"]
        self.spectra = []
        self.res=[]
        self.normalised_datacube=[]
        self.wl_lim=acqui_dict["wl_lim"]
        self.spec_lib = SpectrometerBridge(self.name_spectro, self.integration_time_ms,self.wl_lim)
        self.wavelengths = []
        self.spectro_flag=False
        self.rep=acqui_dict["spectro_scans2avg"]

         # Displaying infos
        self.height = acqui_dict['height']
        self.width = acqui_dict["width"]
        self.interp_method=None
        self.periode_pattern=int(self.rep*self.integration_time_ms)
        if self.periode_pattern<60 :self.periode_pattern=60
        
        # Pattern method infos
        self.pattern_method = acqui_dict['pattern_method']
        self.spatial_res = acqui_dict['spatial_res']
        self.pattern_lib = PatternMethodSelection(self.pattern_method, self.spatial_res, self.height, self.width)
        self.nb_patterns = self.pattern_lib.nb_patterns
        self.seq_basis = ['FourierSplit','FourierShift']
        self.full_basis = ['Addressing','Custom','Hadamard','BlackAndWhite']
        self.pattern_order = []

        self.duration = 0 #Initialise the duration of a measure
        self.normalisation_path=acqui_dict["normalisation_path"]
        self.save_path=''
        
    

    def init_display(self):
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
        if self.pattern_method in self.seq_basis: # Method used to create, display and measure sequentially patterns within a specific basis
            pattern_reduction=[4,3]
            # horizontal vector for the pattern creation
            x = np.arange(0,self.width//pattern_reduction[0],dtype=np.uint8)
            # vertical vector for the pattern creation
            y = np.arange(0,self.height//pattern_reduction[1],dtype=np.uint8)
            # horizontal and vertical array for the pattern creation
            Y, X = np.meshgrid(x, y)
    
            self.pattern_order, freqs = self.pattern_lib.decorator.sequence_order() # Get spatial frequencies list to create patterns
            self.interp_method=cv2.INTER_LINEAR_EXACT
            
            for freq in freqs:
                self.pattern_lib.decorator.sequence.extend(self.pattern_lib.decorator.creation_patterns(X, Y, freq))  # Patterns creations 
            
        elif self.pattern_method in self.full_basis:
            self.pattern_order,freq=self.pattern_lib.decorator.creation_patterns()
            self.interp_method=cv2.INTER_AREA
        self.nb_patterns=self.pattern_lib.nb_patterns=len(self.pattern_lib.decorator.sequence)
        print(f"sequence of {self.pattern_lib.nb_patterns} is ready !")
        
        # Spectrometer connection
        if self.spec_lib.DeviceName=='':
            self.spec_lib.spec_open()
        self.spec_lib.set_integration_time()
        self.wavelengths = self.spec_lib.get_wavelengths()
        self.spectra=np.zeros((self.nb_patterns,len(self.wavelengths)),dtype=np.float32)
    
                    

    def spectrometer_acquisition(self,event):
        """
        spectrometer_acquisition allows to use the spectrometer so that it is synchronised with patterns displays.
    
        Parameters
        ----------
        event : threading.Event 
            event that notifies when pattern is displayed and allow display to continue when cleared.
        config : class
            OPConfig class object.
    
        Returns
        -------
        None. measured spectra are stored in config.
    
        """
        
        cnt=0
        chronograms=np.zeros((self.rep,self.nb_patterns,len(self.wavelengths)))
        coeff=1
        while cnt <self.nb_patterns:            
            if self.spectro_flag: # check to adjust integration time for white pattern
               self.spec_lib.decorator.integration_time_ms=self.integration_time_ms//2
               self.spec_lib.decorator.set_integration_time()
               coeff=self.integration_time_ms/self.spec_lib.decorator.integration_time_ms
            
            if event.is_set():# event set when pattern is displayed
                for k in range(self.rep):
                    chronograms[k,cnt,:]=coeff*self.spec_lib.get_intensities()
                
                if self.spectro_flag: #
                    self.spec_lib.decorator.integration_time_ms=self.integration_time_ms
                    self.spec_lib.decorator.set_integration_time()
                    coeff=1
                    self.spectro_flag=False

                cnt+=1
                event.clear()
            else:
                time.sleep(1e-6)
            
        self.spectra=np.mean(chronograms,0)       
        self.spec_lib.spec_close()

    
    
    def display_sequence(self,event):
        """
        This function allows to display a sequence of patterns.
       
        Parameters
        ----------
        event : threading Event 
            Ensures the synchronisation between displays and measures
        config : class
            OPConfig class object.
    
        Returns
        -------
        None.
    
        """  
        # Initialise cv2 display on the second monitor 
        cv2.namedWindow('ImageWindow', cv2.WINDOW_NORMAL)
        cv2.moveWindow('ImageWindow', screenWidth, 0)
        cv2.setWindowProperty("ImageWindow", cv2.WND_PROP_FULLSCREEN, 1)
        cv2.imshow('ImageWindow',cv2.resize(self.pattern_lib.decorator.sequence[0],(self.width,self.height),interpolation=self.interp_method))
        cv2.waitKey(750) # allows the projector to take the time to display the first pattern, particularly if it is white          
        
        try:
            white_idx=self.pattern_lib.decorator.white_pattern_idx
        except:
            white_idx=-100
        delta_idx=4 if self.pattern_method=='FourierSplit' else 2
        # Display each pattern from the sequence
        for count,pattern in enumerate(self.pattern_lib.decorator.sequence):
            if  count in np.arange(white_idx,white_idx+delta_idx):
                self.spectro_flag=True
           

            cv2.imshow('ImageWindow',cv2.resize(pattern,(self.width,self.height),interpolation=self.interp_method))
            cv2.waitKey(int(self.periode_pattern))
            event.set()
            time.sleep(1e-6)
            while event.is_set():
                time.sleep(1e-6)
            

        cv2.destroyAllWindows()

        
       
        
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
            self.init_display()
            #Threads initialisation
            event=threading.Event()
            patterns_thread = threading.Thread(target=self.display_sequence,args=(event,))
            spectrometer_thread = threading.Thread(target=self.spectrometer_acquisition,args=(event,))
            # Start both display and measure threads
            patterns_thread.start()
            spectrometer_thread.start()
            patterns_thread.join()
            spectrometer_thread.join()

            self.duration = time.time()-begin_acq
            #self.save_acquisition_envi(path)
            
        else:
            cv2.destroyAllWindows()
            pass
            
