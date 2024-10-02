from plugins.spectrometer.Goyalab.goyalab_library import *
import numpy as np

class GoyalabBridge:
    """Class OceanInsightBridge allows to use OceanInsight spectrometers with the ONE-PIX
    kit. Available spectrometers relies on the seabreeze library."""

    def __init__(self,integration_time_ms,gain=5,DEVICE_PORT='/dev/ttyACM0',DEVICE_PORT_BAUDRATE=115200):
                self.integration_time_ms=integration_time_ms
                self.spec=[]
                self.DeviceName=''
                self.gain=gain
                self.DEVICE_PORT=DEVICE_PORT
                self.DEVICE_PORT_BAUDRATE=DEVICE_PORT_BAUDRATE
                self.device_info=0
                self.range_settings=0

    def spec_open(self):
        """
        spec_open allows to initialise the connection with the spectrometer.

        Returns
        -------
        None.

        """
        self.spec= indigo_connect(self.DEVICE_PORT, self.DEVICE_PORT_BAUDRATE)
        # configure the device in the desired mode
        config_lambdamode(True, self.spec)        # Enable lambda mode to get spectral data in nanometers instead of raw pixel values
        config_fullbitmode(True, self.spec)       # Enable fullbit mode to get data in the largest dynamics available on the device
        config_sensor_means(50,self.spec)
        # Set the desired gain, in millidecibels
        config_gain_millidB(1000*np.log10(self.gain), self.spec) # desired gain for the MT9M001 range in 2-15 LINEAR, so i thas to be converted to millidecibels
        self.device_info = read_device_info(self.spec)
        self.range_settings = read_device_range(self.spec)
        self.DeviceName='Goyalab'

    def set_integration_time(self):
        """
        set_integration_time allows to set integration time in milliseconds.

        Returns
        -------
        None.

        """
        config_expousure_time_ms(self.integration_time_ms, self.spec)         # desired exposure time, in milliseconds

    def get_wavelengths(self):
        """
        get_wavelengths allows to get the sampled wavelengths by the spectrometer.

        Returns
        -------
        wl : array of floats
            1D array of the sampled wavelengths.

        """
        if self.device_info.isLambdaModeEnabled:
            wavelengths = np.linspace(self.range_settings.start_wavelength, self.range_settings.stop_wavelength-self.range_settings.step, self.range_settings.nb_points)
        else:
            wavelengths = np.linspace(0, self.device_info.nbPixelsPerLine-1, self.device_info.nbPixelsPerLine)
        return wavelengths
    
    def get_intensities(self):
        """
        get_intensities allows to measure a spectrum.

        Returns
        -------
        spectrum : array of floats
            1D array of spectral measurements.

        """
        
        start_capture(0, self.spec)
        # wait for the device to finish capturing and start transferring data
        while(self.spec.inWaiting() == 0):
            pass
              
        # parse the spectral data
        spectrumData = read_spectrum(self.range_settings, self.device_info, self.spec)
        # convert the spectral data into X/Y arrays
        intensities = [int(x) for x in spectrumData]
        return intensities

    def spec_close(self):
        """
        spec_close allows to end communication with an initialised spectrometer

        Returns
        -------
        None.

        """
        self.spec.close()
