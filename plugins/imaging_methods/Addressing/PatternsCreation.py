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

import PIL.Image
import screeninfo
import plugins.imaging_methods.FIS_common_functions.FIS_common_acquisition as FIS

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
        self.sequence=[]
        self.interp_method=cv2.INTER_AREA
        self.nb_patterns=2

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
        self.patterns_order=['']*self.nb_patterns
        
  
    def creation_patterns(self):
        #parameters to connect by SSH to the GPU server and execute SCP command get/add
        #ip=acqui_dict["IP"]
    
        date = datetime.now().strftime("%Y%m%d_%H%M%S")
        RGB_path= f'PiCamera_{date}.png'

        # Take a picture from the scene 
        # adjust the luminosity to correctly capture RGB image
        root=Tk()
        root.geometry("{}x{}+{}+{}".format(proj_shape.width, proj_shape.height,screenWidth,0))
        root.wm_attributes('-fullscreen', 'True')
        c=Canvas(root,width=proj_shape.width,height=proj_shape.height,bg='black',highlightthickness=0)
        c.pack()
        root.update()
        
        # PiCamera settings
        camera.get_image(tag='Addressing',save_path=RGB_path)
        RGB_img = PIL.Image.open(RGB_path)
        RGB_img= np.asarray(RGB_img)
        RGB_img=apply_corregistration(RGB_img)
        os.remove(RGB_path)
        
        # close black screen
        root.destroy()
        
        self.patterns=self.clustering_method.get_clusters(RGB_img)

        #Add dark pattern
        self.patterns=np.append(self.patterns,np.zeros_like(self.patterns[0,:,:][np.newaxis,:,:],dtype=np.uint8),axis=0)
        self.nb_patterns=np.size(self.patterns,0)
        self.sequence_order()
        return self.patterns

    def save_raw_data(self,acquisition_class,path=None):
        saver=FIS.FisCommonAcquisition(acquisition_class)
        saver.save_raw_data(path=None)