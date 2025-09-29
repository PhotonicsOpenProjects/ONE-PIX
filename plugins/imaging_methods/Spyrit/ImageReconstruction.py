import numpy as np 
import torchvision
import torch
import os 
import glob
import tkinter as Tk
from tkinter import filedialog
from tkinter import *
from spyrit.misc.walsh_hadamard import sequency_perm

from spyrit.core.meas import HadamSplit
from spyrit.core.noise import NoNoise
from spyrit.core.prep import SplitPoisson
from spyrit.core.recon import PseudoInverse
import math
from spyrit.core.noise import Poisson
from spyrit.core.recon import DCNet, PinvNet

from spyrit.core.train import load_net
from spyrit.core.nnet import Unet
from spyrit.misc.sampling import reorder, Permutation_Matrix

from plugins.imaging_methods.FIS_common_functions.FIS_common_reconstruction import (
    FisCommonReconstruction,
)
import json

class Reconstruction:
    """ Class to reconstruct a data cube from Walsh Hadamard splitting ONE-PIX method."""
    def __init__(self,acquisition_dict):
        self.reconstruction_results={}
        self.reconstruction_results["wavelengths"]=acquisition_dict["wavelengths"]
        self.spectra = np.asarray(acquisition_dict["spectra"])
        self.pattern_order = acquisition_dict["patterns_order"]
        spyrit_config_path=os.path.dirname(os.path.abspath(__file__))+f"{os.sep}conf"+f"{os.sep}spyrit_config.json"
        with open(spyrit_config_path) as f:
            spyrit_dict = json.load(f)
        self.cnn_path=spyrit_dict["cnn_path"]



    def onepix2spyrit_mes(self):
        self.spyrit_mes = torch.from_numpy(self.spectra.T).to(dtype=torch.float)   
     
 
    def image_reconstruction(self):

        Cov_rec = np.load(self.cnn_path+'\Cov_64x64.npy')
        title=self.cnn_path+'\cnn_32to64'
        
        Ord_acq = np.ones((32, 32))
        
        Ord_rec = np.ones((64, 64))
        n_sub = math.ceil(32)
        Ord_rec[:,n_sub:] = 0
        Ord_rec[n_sub:,:] = 0
            
        meas = HadamSplit(1024, 64, Ord_rec)
        noise = Poisson(meas, 1) # could be replaced by anything here as we just need to recon
        prep  = SplitPoisson(10, meas)    
        
        
        # unet
        denoi = Unet()
        
        model = DCNet(noise, prep, Cov_rec, denoi)
    
        device='cpu'
        load_net(title, model, device, strict = False)
        model.eval() 
        
        
        model.prep.set_expe()
        model.to(device)
        
        Perm_rec = Permutation_Matrix(Ord_rec)    # from natural order to reconstrcution order 
        Perm_acq = Permutation_Matrix(Ord_acq).T  # from acquisition to natural order
        m = reorder(self.spectra, Perm_acq, Perm_rec)
        with torch.no_grad():
            m_torch = torch.Tensor(m[:2*1024,:]).to(device)
            rec_gpu = model.reconstruct_expe(m_torch.T)
            rec = rec_gpu.cpu().detach().numpy().squeeze()
        self.datacube = rec
        self.datacube=self.datacube.T
        hyperspectral_image=self.datacube
        self.reconstruction_results["reconstructed_data"]=self.hyperspectral_image
        return hyperspectral_image
    
    def get_result_to_plot(self):
        self.result_to_plot=self.fis.get_result_to_plot(self.hyperspectral_image,self.wavelengths)
        self.reconstruction_results["result2plot"]=self.result_to_plot
        return  self.result_to_plot

    def save_reconstructed_image(
        self, header, filename, save_path=None
    ):
        self.fis.save_acquisition_envi(self.reconstruction_results, header, filename, save_path)