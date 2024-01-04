import importlib
import numpy as np
import time

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
    
    def __init__(self,spectro_name,integration_time_ms,wl_lim,repetition):
        # Concrete spectrum implementation dynamic instanciation
        try:
            module_name=f'plugins.spectrometer.{spectro_name}.'
            className=spectro_name+'Bridge'
            module=importlib.import_module(module_name+className)
            classObj = getattr(module, className)
            self.spectrometer = classObj(integration_time_ms)
            self.wl_lim=wl_lim
            self.repetition=repetition
        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + spectro_name + "\" implementation has not been found.")

        # Misc
        self.DeviceName = ''
        self.integration_time_ms=integration_time_ms

    def spec_open(self):
        self.spectrometer.spec_open()
        self.DeviceName =self.spectrometer.DeviceName
        wavelengths=self.spectrometer.get_wavelengths()
        self.idx_wl_lim=[np.abs(wavelengths-self.wl_lim[0]).argmin(),np.abs(wavelengths-self.wl_lim[1]).argmin()]
        

    def set_integration_time(self):
        self.spectrometer.integration_time_ms=self.integration_time_ms
        self.spectrometer.set_integration_time()

    def get_wavelengths(self):
        self.wavelengths=self.spectrometer.get_wavelengths()[self.idx_wl_lim[0]:self.idx_wl_lim[1]]
        return self.wavelengths

    def get_intensities(self):
        spectrum=self.spectrometer.get_intensities()[self.idx_wl_lim[0]:self.idx_wl_lim[1]]
        return spectrum

    def spec_close(self):
        self.spectrometer.spec_close()

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
            repetitions=5
            max_counts = 30000
            self.set_integration_time()
            
            flag = True
            self.spectro_flag=True
            count=0
            delta_wl=round(0.05*np.size(self.get_wavelengths()))
            while flag:
                mes = []
                for acq in range(repetitions):
                    mes.append(self.get_intensities())
                mes = np.mean(np.array(mes), 0)[delta_wl:-delta_wl]
                delta = max(mes)-max_counts
                print(f"Tint{count}={self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")
        
                if (abs(delta)<2500):
                    flag = False
                elif self.integration_time_ms >= 10E3 or self.integration_time_ms==0:
                    flag = False
                    self.spec_close()
                    raise Exception(f"Integration time: {self.integration_time_ms} ms, if you want to continue set the parameter by hand")
                    
                elif (count>=10):
                    flag=False
                    print(f"Measures stopped after {count} iterations. Integration time= {self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")
                else:
                    count+=1
                    flag = True
                    coeff = (max_counts/max(mes))
                    self.integration_time_ms = int(self.integration_time_ms*coeff)
                    self.integration_time_ms = self.integration_time_ms
                    self.set_integration_time()
                    
                self.set_integration_time()
                self.spectro_flag=False
            print(f"Integration time (ms): {self.integration_time_ms}")

    def thread_singlepixel_measure(self,event,spectra):
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
        self.spectra=spectra
        nb_patterns=np.size(spectra,0)
        coeff=1
        while cnt <nb_patterns:
            """            
            if self.spectro_flag: # check to adjust integration time for white pattern
                self.spectrometer.integration_time_ms=self.integration_time_ms//2
                self.set_integration_time()
                coeff=self.integration_time_ms/self.spectrometer.integration_time_ms
            """
            
            
            if event.is_set():# event set when pattern is displayed
                chronograms=[]
                for _ in range(self.repetition):
                    chronograms.append(coeff*self.get_intensities())
                self.spectra[cnt,:]=np.mean(chronograms,0)
                
                """
                if spectro_flag: #
                    self.spectrometer.integration_time_ms=self.integration_time_ms
                    self.spectrometer.set_integration_time()
                    coeff=1
                    spectro_flag=False
                """
                cnt+=1
                event.clear()
            else:
                time.sleep(1e-6)
            
        #spectra=np.mean(chronograms,0)
               
        self.spec_close()

        