import importlib
from plugins.spectrometer.AbstractBridge import AbstractBridge
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
            module='core.spectrometer_bridges'
            className=spectro_name+'Bridge'
            module=importlib.import_module('plugins.spectrometer.spectrometer_bridges.'+className)
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

    def get_optimal_integration_time(self):
            """
            This function allows to automatically set the right integration time for 
            ONE-PIX acqusitions depending on the mesurable optical flux. 
        
            Parameters
            ----------
            config : class
                OPConfig class object.
        
            Returns
            -------
            None. Actualisation of the integration_time_ms parameter of config
        
            """
            
            max_counts = 30000
            self.spec_lib.set_integration_time()
            
            flag = True
            self.spectro_flag=True
            count=0
            delta_wl=round(0.05*np.size(self.spec_lib.get_wavelengths()))
            while flag:
                mes = []
                for acq in range(self.rep):
                    mes.append(self.spec_lib.get_intensities())
                mes = np.mean(np.array(mes), 0)[delta_wl:-delta_wl]
                delta = max(mes)-max_counts
                print(f"Tint{count}={self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")
        
                if (abs(delta)<2500):
                    flag = False
                elif self.spec_lib.integration_time_ms >= 10E3 or self.spec_lib.integration_time_ms==0:
                    flag = False
                    self.spec_lib.spec_close()
                    raise Exception(f"Integration time: {self.spec_lib.integration_time_ms} ms, if you want to continue set the parameter by hand")
                    
                elif (count>=10):
                    flag=False
                    print(f"Measures stopped after {count} iterations. Integration time= {self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")
                else:
                    count+=1
                    flag = True
                    coeff = (max_counts/max(mes))
                    self.integration_time_ms = int(self.integration_time_ms*coeff)
                    self.spec_lib.integration_time_ms = self.integration_time_ms
                    self.spec_lib.set_integration_time()
                    
                self.spec_lib.set_integration_time()
                self.spectro_flag=False
            print(f"Integration time (ms): {self.integration_time_ms}")

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