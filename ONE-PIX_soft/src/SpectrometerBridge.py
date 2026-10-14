import importlib
from src.spectrometer_bridges.AbstractBridge import AbstractBridge

class SpectrometerBridge:
    """
     Allows to build a generic bridge based on a concrete one. Concrete 
     bridge provides correct implementation regarding to spectrometer model 
     use. The generic bridge is an abstract layer that wrap concrete implementation.
    
     :param str spectro_name:
    		Spectrometer concrete bridge implementation:
    		~~~~
     :param float integration_time_ms:
    		spectrometer integration time in milliseconds.
    """
    
    def __init__(self,spectro_name,integration_time_ms):
		# Concrete spectrum implementation dynamic instanciation
        try:
            module='src.spectrometer_bridges'
            className=spectro_name+'Bridge'
            module=importlib.import_module('src.spectrometer_bridges.'+className)
            classObj = getattr(module, className)
            self.decorator = classObj(integration_time_ms)
        except:
            raise Exception("Concrete bridge \"" + spectro_name + "\" implementation has not been found.")
#         if not isinstance(self.decorator, AbstractBridge):
#             raise Exception("Concrete bridge \"" + spectro_name + "\" must implement class bridges.AbstractBridge.")
 		# Misc
        self.DeviceName = ''
        self.integration_time_ms=integration_time_ms
	
    def spec_open(self):
        self.decorator.spec_open()
        self.DeviceName =self.decorator.DeviceName
        
    
    def set_integration_time(self):
        self.decorator.integration_time_ms=self.integration_time_ms
        self.decorator.set_integration_time()
    
    def get_wavelengths(self):
        wl=self.decorator.get_wavelengths()
        return wl
    
    def get_intensities(self):
        spectrum=self.decorator.get_intensities()
        return spectrum
    
    def spec_close(self):
        self.decorator.spec_close()
