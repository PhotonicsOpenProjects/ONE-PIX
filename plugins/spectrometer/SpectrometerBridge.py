import importlib
from src.spectrometer_bridges.AbstractBridge import AbstractBridge
import numpy as np

class SpectrometerBridge:
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
        try:
            module='src.spectrometer_bridges'
            className=spectro_name+'Bridge'
            module=importlib.import_module('src.spectrometer_bridges.'+className)
            classObj = getattr(module, className)
            self.decorator = classObj(integration_time_ms)
            self.idx_wl_lim=wl_lim
        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + spectro_name + "\" implementation has not been found.")

 		# Misc
        self.DeviceName = ''
        self.integration_time_ms=integration_time_ms
    def spec_open(self):
        self.decorator.spec_open()
        self.DeviceName =self.decorator.DeviceName
        wl=self.decorator.get_wavelengths()
        self.idx_wl_lim=[np.abs(wl-self.idx_wl_lim[0]).argmin(),np.abs(wl-self.idx_wl_lim[1]).argmin()]
       
    
    def set_integration_time(self):
        self.decorator.integration_time_ms=self.integration_time_ms
        self.decorator.set_integration_time()
    
    def get_wavelengths(self):
        wl=self.decorator.get_wavelengths()[self.idx_wl_lim[0]:self.idx_wl_lim[1]]
        return wl
    
    def get_intensities(self):
        spectrum=self.decorator.get_intensities()[self.idx_wl_lim[0]:self.idx_wl_lim[1]]
        return spectrum
    
    def spec_close(self):
        self.decorator.spec_close()

    def thread_singlepixel_measure(self,event):
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
        chronograms=np.zeros((self.hardware.repetition,self.nb_patterns,len(self.wavelengths)))
        coeff=1
        while cnt <self.nb_patterns:            
            if self.spectro_flag: # check to adjust integration time for white pattern
               self.hardware.spectrometer.integration_time_ms=self.integration_time_ms//2
               self.hardware.spectrometer.set_integration_time()
               coeff=self.integration_time_ms/self.spec_lib.decorator.integration_time_ms
            
            if event.is_set():# event set when pattern is displayed
                for k in range(self.hardware.repetition):
                    chronograms[k,cnt,:]=coeff*self.spec_lib.get_intensities()
                
                if self.hardware.spectro_flag: #
                    self.hardware.spectrometer.integration_time_ms=self.integration_time_ms
                    self.hardware.spectrometer.set_integration_time()
                    coeff=1
                    self.hardware.spectro_flag=False

                cnt+=1
                event.clear()
            else:
                time.sleep(1e-6)
            
        self.spectra=np.mean(chronograms,0)       
        self.hardware.spectrometer.spec_close()
