import numpy as np 
import matplotlib.pyplot as plt 
import os
import glob
import tkinter as Tk
from tkinter import filedialog
from tkinter import *
import importlib
import platform
from sklearn import mixture
import spectral.io.envi as envi

#%% Raw data pre-treatment

def time_aff_corr(chronograms,time_spectro,time_aff):
    """
    This function automatically corrects the display times according to the 
    measurements of the initialization B&W sequence.

    Parameters
    ----------
    chronograms : array of floats
        3D array of spectra stored in chronological order.
    time_spectro : array of floats
        1D array of time values for each measured spectrum.
    time_aff : array of floats
        1D array of time values of the beginning and the end of projection for each pattern.

    Returns
    -------
    time_aff : array of floats
        corrected array of time values.

    """
    mes_ratio=np.size(time_spectro)/np.size(time_aff)
    if(mes_ratio<1):mes_ratio=int(1/mes_ratio) 
    else: mes_ratio=int(mes_ratio)
    max_pt=int(((-3+np.sqrt(1+np.size(time_aff)))-1)*mes_ratio)
    #chronograms=get_spectra_from_txt(0,max_pt)
    wl_sz=np.size(chronograms,1)
    
    data=np.array(chronograms[2*mes_ratio:max_pt]).reshape(max_pt-2*mes_ratio,wl_sz)[:,wl_sz//2]
    
    gmm = mixture.GaussianMixture(n_components=2)
    gmm.fit(data.reshape(-1,1))
    
    start=np.argmin(data>float(min(gmm.means_)))
    
    dv=abs(gmm.means_[0]-gmm.means_[1])
    start_idx=np.argmax(data[start:]>float(min(gmm.means_))+(dv/2))-1+2*mes_ratio+start
    delay=time_spectro[start_idx]-time_aff[0]
    time_aff=time_aff+delay
    
    return time_aff

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


def load_chronograms():
    """
    This function allows to load saved chronograms with timers of the displays and spectrometers.
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
    chemin_mesure = filedialog.askdirectory(title = "ouvrir le dossier contenant les mesures", initialdir = chemin_script)
    os.chdir(chemin_mesure)
    
    header_name=glob.glob('*.txt')[0]
    acq_data=get_header_data(header_name)
    
    list_nom_mesure = sorted(glob.glob('*.npy'),key=os.path.getmtime)
    
    indice=[x for x, s in enumerate(list_nom_mesure) if "display_time" in s]
    acq_data['time_aff']=np.load(list_nom_mesure[indice[0]])
    
    indice=[x for x, s in enumerate(list_nom_mesure) if "time_spectro" in s]
    acq_data['time_spectro']=np.load(list_nom_mesure[indice[0]])
    
    indice=[x for x, s in enumerate(list_nom_mesure) if "chronograms" in s]
    acq_data['chronograms']=np.load(list_nom_mesure[indice[0]])
    
    indice=[x for x, s in enumerate(list_nom_mesure) if "pattern_order" in s]
    acq_data['pattern_order']=np.load(list_nom_mesure[indice[0]])
    
    indice=[x for x, s in enumerate(list_nom_mesure) if "wavelength" in s]
    acq_data['wavelengths']=np.load(list_nom_mesure[indice[0]])
    
    os.chdir(chemin_script)
    acq_data['time_aff']=time_aff_corr(acq_data['chronograms'],acq_data['time_spectro'],acq_data['time_aff'])
    
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
   
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', 1)
    res={"hyperspectral_image":[],"wavelengths":[]}
    
    if opt==None:
        meas_path = filedialog.askdirectory(title = "Select the folder containing the acquisitions")
    elif opt=='last':
        root_path=os.getcwd()
        path=os.path.join(root_path,'Hypercubes')
        meas_path=max(glob.glob(os.path.join(path, '*/')), key=os.path.getmtime)
       
    else:
        meas_path=opt
        
    hyp_filename=glob.glob(f'{meas_path}/*.hdr')[0]
    data=envi.open(hyp_filename)
    res["hyperspectral_image"]=data.load()
    res["wavelengths"]=np.array(data.bands.centers)
        
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

def preview_chronogram(display_time,time_spectro,chronograms,wavelength):
    """
    This function displays the most intense spectrum of the chronograms and the
    chronogram at the most intense wavelength. Purple vertical bars are timers of displays.

    Parameters
    ----------
    display_time : array of floats
        times of displayed patterns.
    time_spectro : array of floats
        times of each spectrometer's measures.
    chronograms : aray of floats
        array with all spectras saved in the chronological order .
    wavelength : array of floats
        1d array of sampled wavelengths of the spectrometer.

    Returns
    -------
    None.

    """
    
    chronograms=chronograms[:,10:]
    wavelength=wavelength[10:]
    spectre_moy=np.mean(chronograms,0)   
    ind_wl_max=np.argmax(spectre_moy)
    ind_max_chrono=np.argmax(chronograms[:,ind_wl_max])
    
    plt.figure()
    plt.subplot(1,2,1)
    plt.plot(time_spectro,chronograms[:,ind_wl_max],'-*')
    for i in display_time:
        plt.axvline(x=i,c='purple', ls='--')
    plt.subplot(1,2,2)
    plt.plot(wavelength,chronograms[ind_max_chrono,:])


def calculate_pattern_spectrum(display_time,delay_proj,time_spectro,chronograms,target):
    """
    This function calculates from chronograms each pattern mean spectrum.

    Parameters
    ----------
    display_time : array of floats
        times of displayed patterns.
    delay_proj : TYPE
        DESCRIPTION.
    time_spectro : array of floats
        times of each spectrometer's measures.
    chronograms : aray of floats
        array with all spectras saved in the chronological order .
    target : int
        number of spectra to ignore for the mean spectrum calculation.

    Returns
    -------
    spectre_pattern : array of floats
        2D array of spectra for each displayed pattern.

    """
    
    #chronograms=chronograms-np.reshape(np.tile(np.mean(chronograms[:,-100:],1),np.size(chronograms,1)),np.shape(chronograms))
    display_time=display_time+delay_proj
    indice_spectro=[]
    for i in display_time:
        indice_spectro.append(np.abs(time_spectro-i).argmin())
    spectre_pattern=[]
    for j in range(0,np.size(indice_spectro),2):
        value=np.array(chronograms[indice_spectro[j]+target:indice_spectro[j+1]-target])
        
        if np.size(value)==0: 
            spectre_pattern.append(np.zeros_like(spectre_pattern[-1]))
            
        else:
            spectre_pattern.append(np.mean(value,0))
    
    spectre_pattern=np.asarray(spectre_pattern)
    spectre_pattern=spectre_pattern-np.reshape(np.tile(np.mean(spectre_pattern[:,-100:],1),np.size(spectre_pattern,1)),np.shape(spectre_pattern))
    spectre_pattern[0,:]=spectre_pattern[4,:]
    return spectre_pattern



    
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
