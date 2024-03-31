#Import libraries (camera, ssh, scp...)
import os
from tkinter import *
import json
from datetime import datetime
import sys
import cv2
import numpy as np
sys.path.append(f'..{os.sep}..{os.sep}..{os.sep}')
from core.hardware.coregistration_lib import *
from core.hardware.CameraBridge import *
import PIL.Image
import screeninfo
from datetime import date
import time

screenWidth = screeninfo.get_monitors()[0].width
try:
    proj_shape=screeninfo.get_monitors()[1]
except IndexError:
    print('Please use a projector to use ONE-PIX')
import importlib
json_path="../../conf/software_config.json"


class CreationPatterns:
    
    def __init__(self,spatial_res=0,height=0,width=0):
        self.patterns_order=[]
        self.interp_method=cv2.INTER_AREA
        self.nb_patterns=0

        with open(json_path) as f:
            acqui_dict = json.load(f)
        # Read segmentation parameters to apply the selected method
        self.clustering_method_name=acqui_dict["clustering_method"]
        self.clustering_parameters=acqui_dict["clustering_parameters"]

        try:
            #Import patterns creation module specific to the chosen imaging method
            clustering_module=importlib.import_module(f'plugins.imaging_methods.Addressing.segmentation.{self.clustering_method_name}')
            self.clustering_classObj = getattr(clustering_module,'Clustering')
            self.clustering_method = self.clustering_classObj(self.clustering_parameters)
            
        
        except ModuleNotFoundError:
            raise Exception("Concrete bridge \"" + self.clustering_method_name + "\" implementation has not been found.")
    
    def sequence_order(self):
        try:
            self.patterns_order=self.clustering_method.patterns_order
            self.patterns_order.insert(0,'Background')
            self.patterns_order.append('Dark')
        except Exception:
            self.patterns_order=['']*self.nb_patterns
        
  
    def creation_patterns(self):
        #parameters to connect by SSH to the GPU server and execute SCP command get/add
        #ip=acqui_dict["IP"]
    
        date = datetime.now().strftime("%Y%m%d_%H%M%S")
        RGB_path= f'PiCamera_{date}.png'

        # Take a picture from the scene 
        # adjust the luminosity to correctly capture RGB image
        #root=Tk()
        #root.geometry("{}x{}+{}+{}".format(proj_shape.width, proj_shape.height,screenWidth,0))
        #root.wm_attributes('-fullscreen', 'True')
        #c=Canvas(root,width=proj_shape.width,height=proj_shape.height,bg='black',highlightthickness=0)
        #c.pack()
        #root.update()
        reference_image = get_reference_image(grayscale=15)
        # Display the reference image
        show_full_frame(reference_image)
        cv2.waitKey(250)
        
        # PiCamera settings
        #camera.camera_open()
        camera.get_image(tag='Addressing',save_path=RGB_path)
        self.RGB_img = PIL.Image.open(RGB_path)
        self.RGB_img= np.asarray(self.RGB_img)
        self.RGB_img_cor=apply_corregistration(self.RGB_img)
        os.remove(RGB_path)
        
        # close black screen
        hide_full_frame()
        
        self.patterns=self.clustering_method.get_clusters(self.RGB_img_cor)

        #Add dark pattern
        self.patterns=np.append(self.patterns,np.zeros_like(self.patterns[0,:,:][np.newaxis,:,:],dtype=np.uint8),axis=0)
        self.nb_patterns=np.size(self.patterns,0)
        print(self.nb_patterns)
        self.sequence_order()
        #camera.close_camera()
        return self.patterns

    def save_raw_data(self,acquisition_class,path=None):
        
        root_path=os.getcwd()
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
        camera_image_filename=f"camera_image_{fdate}_{actual_time}.png"
        patterns_order_filename=f"patterns_order_{fdate}_{actual_time}.npy"
        masks_filename=f"masks_{fdate}_{actual_time}.npy"
        
        os.mkdir(folder_name)
        os.chdir(folder_name)
        self.save_path=folder_name

        with open(acquisition_class.title_param, "w+") as text_file:
            text_file.write(acquisition_class.header)
        

        
        #save RGB camera image and coregistrated image of the scene
        #acquisition_class.hardware.camera.get_image(tag=None,save_path=f'./{camera_image_filename}')
        #RGB_img = cv2.imread(f'./{camera_image_filename}')
        #RGB_img= np.asarray(RGB_img)
        #RGB_img=apply_corregistration(RGB_img)
        cv2.imwrite(f"RGB_cor_{fdate}_{actual_time}.jpg",self.RGB_img_cor)
        # save raw acquisition data in numpy format
        spectra=acquisition_class.spectra-acquisition_class.spectra[-1,:]
        np.save(acquisition_filename,spectra[:-1,:]) # measured spectra 
        np.save(wavelengths_filename,acquisition_class.hardware.spectrometer.wavelengths) # associated wavelengths
        np.save(patterns_order_filename,acquisition_class.imaging_method.patterns_order)
        np.save(masks_filename,acquisition_class.imaging_method.patterns)
        os.chdir(root_path)