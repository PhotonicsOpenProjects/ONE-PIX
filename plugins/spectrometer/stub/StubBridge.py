import numpy as np 

class StubBridge:
    """ Class OceanInsightBridge allows to use OceanInsight spectrometers with the ONE-PIX
        kit. Available spectrometers relies on the seabreeze library."""
        
    def __init__(self,integration_time_ms):
        self.integration_time_ms=integration_time_ms
        self.spec=[]
        self.DeviceName='stub_spectrometer'
       
        
    def spec_open(self):
        """
        spec_open allows to initialise the connection with the spectrometer.

        Returns
        -------
        None.

        """
        print("Stub_spectrometer connected")
        

            
            
        
    def set_integration_time(self):
        """
        set_integration_time allows to set integration time in milliseconds.        

        Returns
        -------
        None.

        """
        self.integration_time_ms=int(self.integration_time_ms)

        return
        
    
    
    def get_wavelengths(self):
        """
        get_wavelengths allows to get the sampled wavelengths by the spectrometer.

        Returns
        -------
        wl : array of floats
            1D array of the sampled wavelengths.

        """
        wl=np.arange(200,1000,3)
        return wl
    
    def get_intensities(self):
        """
        get_intensities allows to measure a spectrum.

        Returns
        -------
        spectrum : array of floats
            1D array of spectral measurements.

        """
        spectrum=40000*np.random.rand(100,1)
        return spectrum
    
    def spec_close(self):
        """
        spec_close allows to end communication with an initialised spectrometer

        Returns
        -------
        None.

        """
        print(" stub_spectro is close")
    