import seabreeze  #import the seabreeze package to communicate with the spectrometer
seabreeze.use("cseabreeze") #specifie to use the cseabreeze extension 
from seabreeze.spectrometers import Spectrometer

class OceanInsightBridge:
    """ Class OceanInsightBridge allows to use OceanInsight spectrometers with the ONE-PIX
        kit. Available spectrometers relies on the seabreeze library."""
        
    def __init__(self,integration_time_ms):
        self.integration_time_ms=integration_time_ms
        self.spec=[]
        self.DeviceName=''
        
    def spec_open(self):
        """
        spec_open allows to initialise the connection with the spectrometer.

        Returns
        -------
        None.

        """
        try:
            self.spec=Spectrometer.spec=Spectrometer.from_first_available()
            self.spec.open() #open the communication with the spectrometer
            self.DeviceName=str(self.spec.serial_number)
        except seabreeze.cseabreeze.SeaBreezeError as e:
            raise Exception ('No Ocean Insight device was detected : %s'%e)
            
            
        
    def set_integration_time(self):
        """
        set_integration_time allows to set integration time in milliseconds.        

        Returns
        -------
        None.

        """
        if self.integration_time_ms*1e3<self.spec.integration_time_micros_limits[0]:
            raise Exception('Spectrometer saturation at lower integration time. Adapt your acquisition configuration to reduce the optical intensity collected')
            
        else:
            self.spec.integration_time_micros(self.integration_time_ms*1e3)
    
    
    def get_wavelengths(self):
        """
        get_wavelengths allows to get the sampled wavelengths by the spectrometer.

        Returns
        -------
        wl : array of floats
            1D array of the sampled wavelengths.

        """
        wl=self.spec.wavelengths()
        return wl
    
    def get_intensities(self):
        """
        get_intensities allows to measure a spectrum.

        Returns
        -------
        spectrum : array of floats
            1D array of spectral measurements.

        """
        spectrum=self.spec.intensities()
        return spectrum
    
    def spec_close(self):
        """
        spec_close allows to end communication with an initialised spectrometer

        Returns
        -------
        None.

        """
        self.spec.close()
    
    
    
    
    
    
    
    