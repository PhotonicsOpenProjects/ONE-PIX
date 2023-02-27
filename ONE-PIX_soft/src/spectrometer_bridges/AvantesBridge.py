from src.DLL.avaspec import *
import time
import numpy as np

class AvantesBridge:
    """ Class AvantesBridge allows to use Avantes spectrometers with the ONE-PIX
        kit. Available spectrometers relies on the avaspec library."""
        
    def __init__(self,integration_time_ms):
        self.integration_time_ms=integration_time_ms
        self.handle=0
        self.config=0
        self.pixels=0
        self.measconfig=MeasConfigType
        self.DeviceName=''

    def spec_open(self):
        """
        spec_open allows to initialise the connection with the spectrometer.

        Returns
        -------
        None.

        """
        AVS_Init(0)
        NbDev = AVS_GetNrOfDevices() 
        if (NbDev==1):
            mylist = AvsIdentityType()                                                                          # pretty sure these do the same thing but whatever you know it works
            mylist = AVS_GetList(1)
            self.DeviceName= str(mylist[0].SerialNumber.decode("utf-8"))
            
            self.handle = AVS_Activate(mylist[0])
            self.pixels = AVS_GetNumPixels(self.handle)
            self.config = DeviceConfigType()
            ret = AVS_UseHighResAdc(self.handle, True)
            ret = AVS_GetParameter(self.handle, 63484)
            
            
            self.measconfig.m_StartPixel = 0 
            self.measconfig.m_StopPixel = self.pixels - 1 
            self.measconfig.m_IntegrationDelay = 0 
            self.measconfig.m_NrAverages = 1 
            self.measconfig.m_CorDynDark_m_Enable = 0 
            self.measconfig.m_CorDynDark_m_ForgetPercentage = 100 
            self.measconfig.m_Smoothing_m_SmoothPix = 0 
            self.measconfig.m_Smoothing_m_SmoothModel = 0 
            self.measconfig.m_SaturationDetection = 0 
            self.measconfig.m_Trigger_m_Mode = 0 
            self.measconfig.m_Trigger_m_Source = 0 
            self.measconfig.m_Trigger_m_SourceType = 0 
            self.measconfig.m_Control_m_StrobeControl = 0 
            self.measconfig.m_Control_m_LaserDelay = 0 
            self.measconfig.m_Control_m_LaserWidth = 0 
            self.measconfig.m_Control_m_LaserWaveLength = 0.0 
            self.measconfig.m_Control_m_StoreToRam =0
            
        elif (NbDev==0):
            raise Exception('No Avantes device was detected')
        else:
            print('Several Avantes devices were detected. Plug only one device')
  
    def set_integration_time(self):
        """
        set_integration_time allows to set integration time in milliseconds.

        Returns
        -------
        None.

        """
        self.measconfig.m_IntegrationTime = self.integration_time_ms
        ret = AVS_PrepareMeasure(self.handle,self.measconfig)
        
    def get_wavelengths(self):
        """
        get_wavelengths allows to get the sampled wavelengths by the spectrometer.

        Returns
        -------
        wl : array of floats
            1D array of the sampled wavelengths.
        """
        
        wl = np.array(AVS_GetLambda(self.handle))[:self.pixels]

        return wl
    
    def get_intensities(self):
        """
        get_intensities allows to actualise spectrometer's parameters and then
        measure a spectrum.

        Returns
        -------
        spectrum : array
            1D array of spectral measurements.

        """
        
        ret = AVS_Measure(self.handle,0,1)                                     # tell it to scan
        dataready = False                                                      # while the data is false
        while (dataready == False):
            dataready = (AVS_PollScan(self.handle) == True)                    # get the status of data
            time.sleep(0.0001)
     
        spectrum = AVS_GetScopeData(self.handle)[1][:self.pixels]

        return spectrum
    
    def spec_close(self):
        """
        spec_close allows to end communication with an initialised spectrometer

        Returns
        -------
        None.

        """
        AVS_Done()
    
    
    
    
    
    
    
    
    