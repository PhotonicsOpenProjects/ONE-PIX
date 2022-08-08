#Import libraries (camera, ssh, scp...)

import numpy as np
import paramiko
from scp import SCPClient
from picamera import PiCamera
import time
import os
from tkinter import *

#create an SSH Client on the GPU-Server to Up/Download files
def createSSHClient(server, port, user, password):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, port, user, password)
        return client
    
class AdressingPatterns:
    
    def __init__(self,spatial_res):
        self.pattern_order=[]
        self.sequence=[]
        self.nb_patterns=2 #Two patterns at this times : "vegetation and background"
        #The goal is to have 3 patterns --> improve segmentation program (dataset)
        
    def sequence_order(self):
        
        pattern_order=["vegetation","sol"]
        return pattern_order
    
    def creation_patterns(self):

        #parameters to connect by SSH to the GPU server and execute SCP command get/add
        server='192.168.0.107'
        port ='22'
        user ='eflam'
        password='33325daf04'


        ssh = createSSHClient(server, port, user, password) #create a secured connection canal
        scp = SCPClient(ssh.get_transport()) #give secure commands to transfer files

        #adjust the luminosity to correctly capture RGB image
        root_path=os.getcwd()
        root=Tk()
        root.geometry("{}x{}+{}+{}".format(800, 600,1024,0))
        root.wm_attributes('-fullscreen', 'True')
        c=Canvas(root,width=800,height=600,bg='black',highlightthickness=0)
        c.pack()
        root.update()
        
        camera = PiCamera()
        camera.resolution = (1024, 768)
        camera.start_preview()
        camera.shutter_speed=7 * 1176
        camera.vflip=True
        camera.hflip=True
        
        
        #Path to save/retrieve on the gpu server and to save on the rb pi
        RGB_path_GPU ="/Users/eflam/Desktop/stagenokia/RGB"
        RGB_path_onepix = "/home/pi/Desktop/Eflamm_test/RGB_im/img1.jpg"
        
        mask_path_GPU_vege ="/Users/eflam/Desktop/stagenokia/mask/mask_vege.npy"
        mask_path_GPU_back ="/Users/eflam/Desktop/stagenokia/mask/mask_back.npy"
        mask_path_onepix = "/home/pi/Desktop/Eflamm_test/stage_eflamm/mask/"
        
        time.sleep(2)
        camera.start_preview()
        camera.capture(RGB_path_onepix)
        camera.stop_preview()
        camera.close()
        
        root.destroy()
        
        scp.put(RGB_path_onepix,RGB_path_GPU) #upload the RGB  image on the GPU server
        
        
        time.sleep(8) #wait the inference of the GPU.
        # If time.sleep(8) is not enough during the acquisition re-run the code.
        
        
        #while(scp.get(mask_path_GPU_vege,mask_path_onepix)!=0 & scp.get(mask_path_GPU_back,mask_path_onepix)=!0) :
        scp.get(mask_path_GPU_vege,mask_path_onepix)#download from the server the mask that hides the background
        scp.get(mask_path_GPU_back,mask_path_onepix)#download from the server the mask that hides the vegetatio,
        
        pattern_vege=np.load(mask_path_onepix+"mask_vege.npy")
        pattern_back=np.load(mask_path_onepix+"mask_back.npy")
        
        self.pattern_order=self.sequence_order()
        self.sequence=[pattern_vege,pattern_back]
        
        
        return self.pattern_order,[]