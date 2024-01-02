import os
import numpy as np
from datetime import date
import time

class FisCommonAcquisition:
    def __init__(self,acquisition_class):
        self.acquisition_class=acquisition_class


    def save_raw_data(self,path=None):

        if path==None: path=f"..{os.sep}Hypercubes"
        print(path)
        if(os.path.isdir(path)):
            pass
        else:
            os.mkdir(path)
        os.chdir(path)
        
        fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = f"ONE-PIX_raw_acquisition_{fdate}_{actual_time}"
        acquisition_filename = f"spectra_{fdate}_{actual_time}.npy"
        wavelengths_filename = f"wavelengths_{fdate}_{actual_time}.npy"
        camera_image_filename=f"camera_image_{fdate}_{actual_time}.npy"
        patterns_order_filename=f"patterns_order_{fdate}_{actual_time}.npy"
        os.mkdir(folder_name)
        os.chdir(folder_name)
        self.save_path=folder_name

        text_file = open(self.acquisition_class.title_param, "w+")
        text_file.write(self.acquisition_class.header)
        text_file.close()
        # save raw acquisition data in numpy format
        np.save(camera_image_filename,self.acquisition_class.camera_image) #RGB image from camera
        np.save(acquisition_filename,self.acquisition_class.spectra) # measured spectra 
        np.save(wavelengths_filename,self.acquisition_class.hardware.spectrometer.wavelengths) # associated wavelengths
        np.save(patterns_order_filename,self.acquisition_class.imaging_method.patterns_order)
         


   