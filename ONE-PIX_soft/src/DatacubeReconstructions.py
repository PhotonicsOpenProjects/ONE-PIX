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


def load_spectra():
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

def load_hypercube(opt=None):
    """
    This function allows to load saved spectra with timers of the displays and spectrometers.
    at runtime, a window appears to select the folder path in which the data are located. 

    Returns
    -------
    acq_data : dict
        Dictionary containing data extracted from files saved after acquisition to reconstruct data cubes.

    """
   
    # root = Tk()
    # root.withdraw()
    # root.attributes('-topmost', 1)
    res={"hyperspectral_image":[],"wavelengths":[]}
    
    if opt==None:
        if os.path.isdir('./Hypercubes'):
            data_folder='./Hypercubes'
        elif '../Hypercubes':
            data_folder='../Hypercubes'
        else:
            data_folder=os.getcwd()    

        meas_path = filedialog.askdirectory(title = "Select the folder containing the acquisitions",initialdir=data_folder)
    elif opt=='last':
        root_path=os.getcwd()
        path=os.path.join(root_path,'Hypercubes')
        meas_path=max(glob.glob(os.path.join(path, '*/')), key=os.path.getmtime)
       
    else:
        meas_path=opt
        
    hyp_filename=glob.glob(f'{meas_path}/*.hdr')[0]
    info_filename=glob.glob(f'{meas_path}/*.txt')[0]
    data=envi.open(hyp_filename)
    res["hyperspectral_image"]=data.load()
    res["wavelengths"]=np.array(data.bands.centers)
    res['infos']='ONE_PIX_analysis'+meas_path.split('/')[-1][19:]   
    res['pattern_method']=get_header_data(info_filename)['pattern_method']
    return res

def load_analysed_data():
    """
    This function allows to reload already reconstructed data cubes.

    Returns
    -------
    data_cube : array of floats
        3D array of spectra constituting an image data cube.
    wavelengths : array of floats
         wavelengths sampled by the spectrometer.

    """
    chemin_script = os.getcwd()
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', 1)
    chemin_mesure = filedialog.askopenfilename(title = "Select the file containing the analsed data", initialdir = chemin_script)
    #os.chdir(chemin_mesure)
    data=np.load(chemin_mesure,allow_pickle=True)
    data_cube=data.item().get('data_cube')
    wavelengths=data.item().get('wavelengths')
    return data_cube,wavelengths

    
def snr_filt(self,spectre_desplit,noise_level=500):
    """
    snr_filt filters spectra in which the maximum intensity is lower than a defined level.

    Parameters
    ----------
    spectre_desplit : array of floats
        2D array of spectra.
    noise_level : float, optional
        minimum accepted intensity level. The default is 500.

    Returns
    -------
    spectre_desplit : array of floats
        filtered 2D array of spectra.

    """
    M=np.max(abs(spectre_desplit),axis=1)
    idx_noise=np.squeeze(np.array(np.where(M<noise_level)))
    spectre_desplit[idx_noise,:]=0
    return spectre_desplit



#%% method Selection

class OPReconstruction:
    """ Class OPReconstruction to reconstruct datacubes according to a ONE-PIX method"""
    def __init__(self,imag_method,spectra,pattern_order):
        self.imag_method=imag_method
        self.spectra=spectra 
        
        self.pattern_order=pattern_order
        self.hyperspectral_image=[]
        self.whole_spectrum=[]
        
        try:
            module='src.reconstructions_methods'
            className=imag_method+'Reconstruction'
            module=importlib.import_module('src.reconstructions_methods.'+className)
            classObj = getattr(module, className)
            self.decorator = classObj(spectra,pattern_order)
        except:
            raise Exception("Concrete bridge \"" + imag_method + "\" implementation has not been found.")
#         if not isinstance(self.decorator, AbstractBridge):
#             raise Exception("Concrete bridge \"" + spectro_name + "\" must implement class bridges.AbstractBridge.")
         
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
        if self.imag_method in ['FourierSplit','FourierShift']:
            self.hyperspectral_image=np.abs(np.fft.ifftn(self.whole_spectrum,axes=(0,1)))
        
        elif self.imag_method=='Hadamard':
            self.hyperspectral_image=self.Hadamard_reconstruction()
