import numpy as np 
import matplotlib.pyplot as plt 
import os
import glob
import tkinter as Tk
from tkinter import filedialog
from tkinter import *
import importlib
from sklearn import mixture
import spectral.io.envi as envi
import time
#%% Raw data pre-treatment


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
    
    header=[]
    with open(path, 'r') as file:
       for line in file.readlines():
           header.append(line.split(':'))
    acq_data=dict()
    acq_data['Acquisition_name']=header[0][0][8:]
    for x in header:
        if x[0].strip()=='Acquisition method':
            acq_data['pattern_method']=x[1].strip()
        
        if x[0].strip()=='Integration time':
            acq_data['integration_time_ms']=float(x[1].strip()[:-2])
    
    return acq_data


#%% method Selection

class OPReconstruction:
    """ Class OPReconstruction to reconstruct datacubes according to a ONE-PIX method"""
    def __init__(self,acq=acq):

        if acq:
            self.imaging_method=acq.imaging_method
            self.spectra=acq.spectra
            self.pattern_order=acq.pattern_order
        else :
            self.load_raw_data()
        
    
    def load_raw_data():
        """
        This function allows to load saved spectra with timers of the displays and spectrometers.
        at runtime, a window appears to select the folder path in which the data are located. 

        Returns
        -------
        acq_data : dict
            Dictionary containing data extracted from files saved after acquisition to reconstruct data cubes.

        """
    
        
        chemin_script = os.getcwd()
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', 1)
        chemin_mesure = filedialog.askdirectory(title = "Select the folder containing the acquisitions", initialdir = chemin_script)
        os.chdir(chemin_mesure)
        
        header_name=glob.glob('*.txt')[0]
        acq_data=get_header_data(header_name)
        
        list_nom_mesure = sorted(glob.glob('*.npy'),key=os.path.getmtime)
        
        indice=[x for x, s in enumerate(list_nom_mesure) if "spectra" in s]
        acq_data['spectra']=np.load(list_nom_mesure[indice[0]])
        
        indice=[x for x, s in enumerate(list_nom_mesure) if "wavelengths" in s]
        acq_data['wavelengths']=np.load(list_nom_mesure[indice[0]])
        
        indice=[x for x, s in enumerate(list_nom_mesure) if "pattern_order" in s]
        acq_data['pattern_order']=np.load(list_nom_mesure[indice[0]])
        
        os.chdir(chemin_script)
        
        return acq_data

         
    def nan_corr(self):
        """
        nan_corr allows to filter nan from acquired spectra

        Returns
        -------
        None.

        """
        try:
            idx_nan=np.argwhere(np.isnan(self.spectra))[0,:-1]
            self.spectra[idx_nan,:]=self.spectra[idx_nan-1,:]
        except IndexError:
            pass
        

    def Selection(self):
        """
        This function allows to reconstruct spatial spectra and images data cubes.
        These data are stored in the OPReconstruction class object.

        Returns
        -------
        None.

        """
        self.nan_corr()
        self.whole_spectrum,self.hyperspectral_image=self.decorator.datacube_reconstruction()
        
       
    def image_reconstruction(self):
        """
        image_reconstruction allows to reconstruct an image data cube from an actualised 
        spatial spectra data cube. Both are stored in the HSPIReconstruction class object.

        Returns
        -------
        None.

        """
        self.recontruct_image=self.imaging_method.reconstructionMethod.reconstruct()
    
    def save_reconstruct_image(self):
        self.imgaging_method.reconstructionMethod.save()
        
    

