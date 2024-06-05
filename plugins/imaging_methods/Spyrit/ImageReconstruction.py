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
from sampling import reorder, Permutation_Matrix

import json

class Reconstruction:
    """ Class to reconstruct a data cube from Walsh Hadamard splitting ONE-PIX method."""
    def __init__(self,spectra,pattern_order):


    
        self.spectra=spectra
        self.pattern_order=pattern_order

    def onepix2spyrit_mes(self):
        self.spyrit_mes = torch.from_numpy(self.spectra.T).to(dtype=torch.float)   
     
 
    def image_reconstruction(self):

        chemin_script = os.getcwd()
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', 1)
        cnn_path = filedialog.askdirectory(title = "Select the folder containing cnn model", initialdir = chemin_script)
        os.chdir(cnn_path)


    
        chemin_script = os.getcwd()
        Cov_rec = np.load(cnn_path+'\Cov_64x64.npy')
        title=chemin_script+'\cnn_32to64'
        
        
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
        
        # or 
        # denoi = nn.Identity()
        # model = DCNet(noise, prep, Cov_rec, denoi)
    
    
        
        load_net(title, model, device, strict = False)
        model.eval() 
        
        
        model.prep.set_expe()
        model.to(device)
        
        Perm_rec = Permutation_Matrix(Ord_rec)    # from natural order to reconstrcution order 
        Perm_acq = Permutation_Matrix(Ord_acq).T  # from acquisition to natural order
        m = reorder(self.onepix_mes["spectra"], Perm_acq, Perm_rec)
        print(np.shape(m))
        with torch.no_grad():
            m_torch = torch.Tensor(m[:2*1024,:]).to(device)
            rec_gpu = model.reconstruct_expe(m_torch.T)
            rec = rec_gpu.cpu().detach().numpy().squeeze()
        print(np.shape(rec))
        self.datacube = rec
        self.datacube=self.datacube.T
        
        return hyperspectral_image

    def save_reconstructed_image(self,datacube,wavelengths,header,filename,save_path=None):
        saver=FisCommonReconstruction()
        saver.save_acquisition_envi(datacube,wavelengths,header,filename,save_path)