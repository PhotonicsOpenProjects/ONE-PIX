"""
@author:PhotonicsOpenProject
Modified and traducted by Leo Brecheton Wed Jul 19 18:32:47 2023

"""
#Import libraries (camera, ssh, scp...)
import numpy as np
import time
import os
from tkinter import *
import json
from datetime import datetime
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from src.coregistration_lib import *
import cv2
import sys
from labelme.label_file import LabelFile
import labelme.utils
import os
from datetime import date
import PIL.Image

def kmeans_LAB(img,nb_clust):
    
    Z = img.reshape((-1,3))
    Z = np.float32(Z)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    ret,label,center=cv2.kmeans(Z,nb_clust,None,criteria,10,cv2.KMEANS_RANDOM_CENTERS)

    center = np.uint8(center)
    res = center[label.flatten()]
    res2 = res.reshape((img.shape))
    res2=np.sum(res2,-1)
    cluster_values=np.unique(res2)
    masks=[]
    class_ids=[]
    i=1
    for clust_value in cluster_values :
        stack=np.zeros(np.shape(res2))
        stack[np.where(res2==clust_value)]=255
        masks.append(stack)
        class_ids.append("clust "+str(i))
        i=i+1
    masks=np.asarray(masks)
    return masks

def k_means2gray(im):
    shape = im.shape
    im2 = im.reshape(shape[0],-1)
    b = np.zeros((shape[1]))
    for i in range(im2.shape[0]):
        b[im[i,:]!=0]=i
    return b.reshape(np.asarray(shape)[-1:])

def Niagara_means(IMG, segm_settings = [2,2]):
    B = cv2.cvtColor(IMG, cv2.COLOR_BGR2RGB)
    B = cv2.cvtColor(B, cv2.COLOR_RGB2LAB)
    B[:,:,0] = B[:,:,0].mean()*np.ones(B[:,:,0].shape)
    IM = cv2.cvtColor(B, cv2.COLOR_LAB2RGB)
    (L,l, any) = IM.shape
    im = IM.reshape(-1,3)
    
    labels = np.ones(L*l)
    labels[:] = k_means2gray(kmeans_LAB(im[:], segm_settings[0]))
    fond = []
    fond.append(labels == np.bincount(np.int8(labels)).argmax())
    masks = [labels != np.bincount(np.int8(labels)).argmax()]
    #print(segm_settings[0])
    for i in segm_settings[1:]:
        #print(i)
        temp_mask = []
        for j in range(len(masks)):
            #print("len: ",len(masks))
            labels = -1 * np.ones(L*l)
            labels[masks[j]] = k_means2gray(kmeans_LAB(im[masks[j]], i))
            labels+=1 # to exclude commun labels with bg
            temp_mask += [labels == k for k in np.unique(labels) if k!=0]
        masks = temp_mask
    masks = fond + masks
    return [np.uint8(255*masks[m]).reshape(L,l) for m in range(len(masks))]

def label2mask(json_file):
    
    #print(os.listdir())
    label_file = LabelFile(json_file)
    img = labelme.utils.img_data_to_arr(label_file.imageData)
    
    label_name_to_value = {"_background_": 0}
    
    for shape in sorted(label_file.shapes, key=lambda x: x["label"]):
        label_name = shape["label"]
        if label_name in label_name_to_value:
            label_value = label_name_to_value[label_name]
        else:
            label_value = len(label_name_to_value)
            label_name_to_value[label_name] = label_value
    lbl, _ = labelme.utils.shapes_to_label(
        img.shape, label_file.shapes, label_name_to_value
    )
    
    nb_clust=len(label_name_to_value)
    value_in_lbl=np.unique(lbl)
    
    masks=[]
    for value in value_in_lbl: 
        idx=np.where(lbl==value)
        mask=np.zeros(np.shape(lbl))
        mask[idx]=255
        masks.append(mask)
        
    #masks.append(masks.pop(0))
    masks=np.asarray(masks)
    return masks

def realtime_labelme(img):
    fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
    actual_time = time.strftime("%H-%M-%S")  # get the current time
    image_name = f"img_{fdate}_{actual_time}.jpg"
    cv2.imwrite(image_name,cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    os.system('labelme '+ image_name +' -O '+image_name[:-4]+'.json')
    json_file=image_name[:-4]+'.json'
    masks=label2mask(json_file)
    
    os.remove(json_file)
    os.remove(image_name)
    return masks



class AddressingPatterns:
    
    def __init__(self,spatial_res):
        self.pattern_order=[]
        self.sequence=[]
        self.nb_patterns=2 #Two patterns at this times : "vegetation and background"
        #The goal is to have 3 patterns --> improve segmentation program (dataset)
        
    def sequence_order(self):
        
        
        pattern_order=["vegetation","sol"]
        return pattern_order


    
    def creation_patterns(self):
        json_path="../acquisition_param_ONEPIX.json"
        f = open(json_path)
        acqui_dict = json.load(f)
        f.close()
        #parameters to connect by SSH to the GPU server and execute SCP command get/add
        ip=acqui_dict["IP"]
        

        date = datetime.now().strftime("%Y%m%d_%H%M%S")
        RGB_path= f'PiCamera_{date}.png'


        #adjust the luminosity to correctly capture RGB image
        root=Tk()
        root.geometry("{}x{}+{}+{}".format(800, 600,1024,0))
        root.wm_attributes('-fullscreen', 'True')
        c=Canvas(root,width=800,height=600,bg='black',highlightthickness=0)
        c.pack()
        root.update()
        
        # PiCamera settings
        get_picture(tag='Addressing',save_path=RGB_path)
        RGB_img = PIL.Image.open(RGB_path)
        RGB_img= np.asarray(RGB_img)
        RGB_img=apply_corregistration(RGB_img,'../acquisition_param_ONEPIX.json')
        os.remove(RGB_path)
        
        # close black screen
        root.destroy()
        

        if type(acqui_dict['spatial_res'])==list:
            print(acqui_dict['spatial_res'])
            masks= Niagara_means(RGB_img,acqui_dict['spatial_res'])
        elif acqui_dict['spatial_res']=='manual_segmentation':
            masks = realtime_labelme(RGB_img)
        
        #Add dark pattern
        masks=np.append(masks,np.zeros_like(masks[0,:,:][np.newaxis,:,:],dtype=np.uint8),axis=0)

        self.nb_patterns=np.size(masks,0)

        self.sequence = masks
        return self.pattern_order,[]
