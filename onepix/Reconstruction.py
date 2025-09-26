import numpy as np
import os
import glob
from datetime import date
import time
from tkinter import *
from tkinter.filedialog import askdirectory
import json
from onepix.ImagingMethodBridge import *

import logging
from onepix.logging_config import root  
logger = logging.getLogger(__name__)


def get_header_data(path):
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

    header = []
    with open(path, "r") as file:
        for line in file.readlines():
            header.append(line.split(":"))
    acq_data = dict()
    acq_data["acquisition_name"] = header[0][0][8:]
    for x in header:
        if x[0].strip() == "Imaging method":
            acq_data["imaging_method_name"] = x[1].strip()

        if x[0].strip() == "Integration time":
            acq_data["integration_time_ms"] = float(x[1].strip()[:-2])
    logging.info("header data is loaded")
    return acq_data


# %% method Selection


class Reconstruction:
    """Class OPReconstruction to reconstruct datacubes according to a ONE-PIX method"""

    def __init__(self, acquisition_dict=None,plot_result=False):

        self.acquisition_dict = acquisition_dict
        self.reconstruction_results={}
        self.plot_result=plot_result
        if acquisition_dict is None:
            self.acquisition_dict=self.load_acquisition_results()
            print(list(self.acquisition_dict.keys()))

        

        self.imaging_method_name = self.acquisition_dict["imaging_method_name"]
        print("imaging_method_name :", self.imaging_method_name )
        self.spectra = self.acquisition_dict["spectra"]
        self.pattern_order = self.acquisition_dict["patterns_order"]
        self.wavelengths = self.acquisition_dict["wavelengths"]
        self.imaging_method_param=acquisition_dict


        self.spatial_res = 0
        self.height = 0
        self.width = 0
        self.imaging_method = ImagingMethodBridge(self.imaging_method_name,self.height, self.width,plot_result=self.plot_result)
        logging.info("Reconstruction class is init")


    def load_acquisition_results(self):
        """
        Cherche un fichier 'acquisition_results_*.json' dans folder_path,
        et le charge en dict Python.
        """
        # chemin complet du script
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        parent_dir = os.path.dirname(script_dir)
        measure_dir = os.path.join(parent_dir, "measure")
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", 1)
        folder_path = askdirectory(
            title="Select the folder containing the acquisitions",
            initialdir=measure_dir,
        )
        for fname in os.listdir(folder_path):
            if fname.startswith("acquisition_results_") and fname.endswith(".json"):
                fpath = os.path.join(folder_path, fname)
                print(fpath)
                with open(fpath, "r", encoding="utf-8") as f:
                    acquisition_results=json.load(f)
                    print(list(acquisition_results.keys()))

                    return acquisition_results
        
        # Si aucun fichier trouvé
        raise FileNotFoundError("⚠️ Aucun fichier acquisition_results_*.json trouvé dans ce dossier")


    def nan_corr(self):
        """
        nan_corr allows to filter nan from acquired spectra

        Returns
        -------
        None.

        """
        try:
            idx_nan = np.argwhere(np.isnan(self.spectra))[0, :-1]
            self.spectra[idx_nan, :] = self.spectra[idx_nan - 1, :]
        except IndexError:
            pass

    def data_reconstruction(self):
        """
        image_reconstruction allows to reconstruct an image data cube from an actualised
        spatial spectra data cube. Both are stored in the HSPIReconstruction class object.

        Returns
        -------
        None.

        """
        self.imaging_method.reconstruction(self.acquisition_dict,plot_result=self.plot_result)
        self.reconstruction_results=self.imaging_method.reconstruction_results
        logging.info("raw datas are reconstructed now")
        if self.plot_result:
            logging.info("plot result is created")


    def create_plot_result(self):
        self.imaging_method.create_plot_result()


    def save_reconstructed_image(self, filename, save_path):
        header = self.create_reconstruction_header()
        self.imaging_method.image_reconstruction_method.save_reconstructed_image(
            self.imaging_method.reconstructed_image,
            self.wavelengths,
            header,
            filename,
            save_path,
        )
        logging.info(f'reconstructed datas are saved at {save_path}')

    def create_reconstruction_header(self):
        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        # Header
        if type(self.acquisition_dict) is dict:
            header = (
                f"ONE-PIX_reconstructed_acquisition_{fdate}_{actual_time}"
                + "\n"
                + "--------------------------------------------------------"
                + "\n"
                + "\n"
                + f"Imaging method: {self.imaging_method_name}"
                + "\n"
            )
        else:
            self.acquisition_dict.create_acquisition_header()
            header=self.acquisition_dict.header

        return header
