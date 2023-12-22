import os
import numpy as np
from datetime import date
import time

class FisCommonAcquisition:
    def __init__(self,acquisition_class):
        self.acquisition_class=acquisition_class


    def save_raw_data(self,path=None):

        if path==None: path=f"..{os.sep}Hypercubes"
        if(os.path.isdir(path)):
            pass
        else:
            os.mkdir(path)
        os.chdir(path)
        
        fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = f"ONE-PIX_raw_acquisition_{fdate}_{actual_time}"
        acquisition_filename = f"spectra_{fdate}_{actual_time}.npy"
        wavelengths_filename = f"wavelenths_{fdate}_{actual_time}.npy"
        os.mkdir(folder_name)
        os.chdir(folder_name)
        self.save_path=folder_name

                    
        # Header
        title_param = f"Raw_acquisition_parameters_{fdate}_{actual_time}.txt"
        header = f"ONE-PIX_raw_acquisition_{fdate}_{actual_time}"+"\n"\
            + "--------------------------------------------------------"+"\n"\
            + "\n"\
            + f"Imaging method: {self.acquisition_class.imaging_method_name}"+"\n"\
            + "Acquisition duration: %f s" % self.acquisition_class.duration+"\n" \
            + f"Spectrometer {self.acquisition_class.hardware.name_spectro} : {self.acquisition_class.hardware.spectrometer.DeviceName}"+"\n"\
            + f"Camera: {self.acquisition_class.hardware.name_camera}" +"\n"\
            + "Number of projected patterns: %d" % self.acquisition_class.nb_patterns+"\n" \
            + "Height of pattern window: %d pixels" % self.acquisition_class.height+"\n" \
            + "Width of pattern window: %d pixels" % self.acquisition_class.width+"\n" \
            + "Number of spectral measures per pattern: %d  " %self.acquisition_class.hardware.repetition+"\n" \
            + "Integration time: %d ms" % self.acquisition_class.hardware.spectrometer.integration_time_ms+"\n" 
    
    
        text_file = open(title_param, "w+")
        text_file.write(header)
        text_file.close()
        # save raw acquisition data in numpy format
        self.acquisition_class.hardware.camera.save_image(path=None) #RGB image from camera
        
        np.save(acquisition_filename,self.acquisition_class.spectra) # measured spectra 
        np.save(wavelengths_filename,self.acquisition_class.wavelengths) # associated wavelengths
        
         


   