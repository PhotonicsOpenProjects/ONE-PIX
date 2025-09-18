# Import libraries (camera, ssh, scp...)
import os
from tkinter import *
import json
from datetime import datetime
import sys
import cv2
import numpy as np

from onepix.hardware.coregistration_lib import *
from onepix.hardware.CameraBridge import *
import PIL.Image
import screeninfo
from datetime import date
import time

screenWidth = screeninfo.get_monitors()[0].width
try:
    proj_shape = screeninfo.get_monitors()[1]
except IndexError:
    print("Please use a projector to use ONE-PIX")
import importlib

from pathlib import Path


def to_serializable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()  # conversion numpy -> list
    return str(obj)  # fallback si jamais il y a d’autres objets non sérialisables

class CreationPatterns:

    def __init__(self, height=0, width=0):
        self.acquisition_results={}
        self.patterns_order = []
        self.interp_method = cv2.INTER_AREA
        self.nb_patterns = 0
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        print("the base path is  :",base_path)
        self.imaging_config_path = os.path.join(base_path, "Adressing_method_param.json")
        print("the full path  base path is  :",self.imaging_config_path)

        with open(self.imaging_config_path) as f:
            acqui_dict = json.load(f)
        # Read segmentation parameters to apply the selected method
        self.clustering_method_name = acqui_dict["clustering_method"]
        self.clustering_parameters = acqui_dict["clustering_parameters"]

        try:
            # Import patterns creation module specific to the chosen imaging method
            clustering_module = importlib.import_module(
                f"plugins.imaging_methods.Addressing.segmentation.{self.clustering_method_name}"
            )
            self.clustering_classObj = getattr(clustering_module, "Clustering")
            self.clustering_method = self.clustering_classObj(
                self.clustering_parameters
            )

        except ModuleNotFoundError:
            raise Exception(
                'Concrete bridge "'
                + self.clustering_method_name
                + '" implementation has not been found.'
            )

    def sequence_order(self):
        try:
            self.patterns_order = self.clustering_method.patterns_order
            self.patterns_order.insert(0, "Background")
            self.patterns_order.append("Dark")
            self.acquisition_results["patterns_order"]= self.patterns_order
        except Exception:
            self.patterns_order = [""] * self.nb_patterns
            self.acquisition_results["patterns_order"]= self.patterns_order

    def creation_patterns(self):
        # parameters to connect by SSH to the GPU server and execute SCP command get/add
        # ip=acqui_dict["IP"]

        date = datetime.now().strftime("%Y%m%d_%H%M%S")
        RGB_path = f"PiCamera_{date}.png"

        # Take a picture from the scene
        # adjust the luminosity to correctly capture RGB image
        # root=Tk()
        # root.geometry("{}x{}+{}+{}".format(proj_shape.width, proj_shape.height,screenWidth,0))
        # root.wm_attributes('-fullscreen', 'True')
        # c=Canvas(root,width=proj_shape.width,height=proj_shape.height,bg='black',highlightthickness=0)
        # c.pack()
        # root.update()
        reference_image = get_reference_image(grayscale=15)
        # Display the reference image
        show_full_frame(reference_image)
        cv2.waitKey(250)

        # PiCamera settings
        # camera.camera_open()
        camera.get_image(tag="Addressing", save_path=RGB_path)
        self.RGB_img = PIL.Image.open(RGB_path)
        self.RGB_img = np.asarray(self.RGB_img)
        self.RGB_img_cor = apply_corregistration(self.RGB_img)
        os.remove(RGB_path)
        self.acquisition_results["rgb"]=self.RGB_img_cor

        # close black screen
        hide_full_frame()

        self.patterns = self.clustering_method.get_clusters(self.RGB_img_cor)

        # Add dark pattern
        self.patterns = np.append(
            self.patterns,
            np.zeros_like(self.patterns[0, :, :][np.newaxis, :, :], dtype=np.uint8),
            axis=0,
        )
        self.nb_patterns = np.size(self.patterns, 0)
        #(self.nb_patterns)
        self.sequence_order()
        # camera.close_camera()
        self.acquisition_results["patterns"]=self.patterns
        return self.patterns
    


