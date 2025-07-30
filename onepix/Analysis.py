from onepix.ImagingMethodBridge import *
import os

import glob
from tkinter import *
from tkinter import filedialog
import json
import numpy as np

import logging
from onepix.logging_config import root  

from datetime import date
import time


logger = logging.getLogger(__name__)

class Analysis:
    def __init__(self, rec=None, data_path=None):
        self.data_path = data_path
        if rec is None:
            self.read_header()
            self.imaging_method = ImagingMethodBridge(self.imaging_method_name)
            self.imaging_method.analysis(self.data_path)
            self.load_data(self.data_path)
            self.reconstructed_data = (
                self.imaging_method.image_analysis_method.reconstructed_data
            )
            self.wavelengths = self.imaging_method.image_analysis_method.wavelengths

        else:
            self.imaging_method_name = rec.imaging_method_name
            self.reconstructed_data = rec.imaging_method.reconstructed_image
            self.wavelengths = rec.wavelengths
            self.imaging_method = ImagingMethodBridge(self.imaging_method_name)
            self.imaging_method.analysis(self.data_path)

        self.software_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"..{os.sep}conf",
            "software_config.json",
        )
        with open(self.software_config_path) as f:
            software_dict = json.load(f)
        self.normalisation_path = software_dict["normalisation_path"]
        self.normalised_data = []
        logging.info("onepix Analysis Class is init")

    def read_header(self):
        """
        This function allows to generate a dictionnary containing acquisition data
        useful for the data cube reconstruction.

        Parameters
        ----------
        path : str
            Header file path

        Returns
        -------
        acq_data : dict
            Dictionnary containing acquisition data.

        """
        chemin_script = os.getcwd()
        if self.data_path is None:
            try:
                root = Tk()
                root.withdraw()
                root.attributes("-topmost", 1)
                self.data_path = filedialog.askdirectory(
                    title="Select the folder containing the acquisitions",
                    initialdir="../Hypercubes",
                )

            except Exception as e:
                print(e)
        os.chdir(self.data_path)
        header_filepath = glob.glob("*.txt")[0]
        header = []
        with open(header_filepath, "r") as file:
            for line in file.readlines():
                header.append(line.split(":"))
            acq_data = dict()
            acq_data["Acquisition_name"] = header[0][0][8:]
            for x in header:
                if x[0].strip() == "Imaging method":
                    acq_data["imaging_method"] = x[1].strip()

        os.chdir(chemin_script)
        self.imaging_method_name = acq_data["imaging_method"]

    def load_data(self, path=None):
        self.imaging_method.image_analysis_method.load_reconstructed_data(path)
        logging.info(f"data are loaded from {path}")

    def data_normalisation(self,ref_data,data=None):
        
        self.normalised_data = self.imaging_method.image_analysis_method.data_normalisation(
            ref_data,data)
        logging.info(f"data are now  normalized")
       
    def get_rgb_image(self, datacube, wavelengths):
        rgb_image = self.imaging_method.image_analysis_method.get_rgb_image(
            datacube, wavelengths
        )
        logging.info(f"RGB image from datacube is created")
        return rgb_image

    def plot_rgb_image(self):
        self.imaging_method.image_analysis_method.plot_reconstructed_image(
            self.reconstructed_image, self.wavelengths
        )
    def save_analysed_image(self, filename, save_path):
        header = self.create_analysed_header()
        self.imaging_method.image_analysis_method.save_analysed_image(
            self.reconstructed_data,
            self.wavelengths,
            header,
            filename,
            save_path,
        )
        logging.info(f'reconstructed datas are saved at {save_path}')

    def create_analysed_header(self):
        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        header = (
            f"ONE-PIX_analysed_data_{fdate}_{actual_time}"
            + "\n"
            + "--------------------------------------------------------"
            + "\n"
            + "\n"
            + f"Imaging method: {self.imaging_method_name}"
            + "\n"
        )


        return header
    
