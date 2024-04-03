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
    acq_data['acquisition_name']=header[0][0][8:]
    for x in header:
        if x[0].strip()=='Imaging method':
            acq_data['imaging_method']=x[1].strip()
        
        if x[0].strip()=='Integration time':
            acq_data['integration_time_ms']=float(x[1].strip()[:-2])
    
    return acq_data

class onepix2spyrit :

    def load_onepix_mes(self):
        """
        This function allows to load saved spectra with timers of the displays and spectrometers.
        at runtime, a window appears to select the folder path in which the data are located. 

        Returns
        -------
        acq_data : dict
            Dictionary containing data extracted from files saved after acquisition to reconstruct data cubes.

        """
    
        try:
            chemin_script = os.getcwd()
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', 1)
            chemin_mesure = filedialog.askdirectory(title = "Select the folder containing the acquisitions", initialdir = chemin_script)
            os.chdir(chemin_mesure)
            
            header_name=glob.glob('*.txt')[0]
            self.onepix_mes=get_header_data(header_name)
            
            list_nom_mesure = sorted(glob.glob('*.npy'),key=os.path.getmtime)
            
            indice=[x for x, s in enumerate(list_nom_mesure) if "spectra" in s]
            self.onepix_mes['spectra']=np.load(list_nom_mesure[indice[0]])
            
            indice=[x for x, s in enumerate(list_nom_mesure) if "wavelengths" in s]
            self.onepix_mes['wavelengths']=np.load(list_nom_mesure[indice[0]])
            
            indice=[x for x, s in enumerate(list_nom_mesure) if "patterns_order" in s]
            self.onepix_mes['patterns_order']=np.load(list_nom_mesure[indice[0]])
            
            os.chdir(chemin_script)
        except Exception as e:
            print(e)

    def onepix2spyrit_mes(self):


        # hpos=self.onepix_mes["spectra"][::2,:]
        # hneg=self.onepix_mes["spectra"][1::2,:]
        # print(hpos.shape)
        # print(hneg.shape)
        
        # hpos_right_order = sequency_perm(hpos)
        # hneg_right_order = sequency_perm(hneg)

        # #h_right_order_prep = sequency_perm(hpos-hneg)

        # h_right_order=np.zeros(np.shape(self.onepix_mes["spectra"]))
        # print(h_right_order.shape)

        # h_right_order[::2,:]  = hpos_right_order
        # h_right_order[1::2,:] = hneg_right_order

        # self.spyrit_mes = torch.from_numpy(h_right_order.T).to(dtype=torch.float)
        self.spyrit_mes = torch.from_numpy(self.onepix_mes["spectra"].T).to(dtype=torch.float)
        #self.spyrit_mes = torch.from_numpy(h_right_order_prep.T).to(dtype=torch.float)


        # from spyrit.misc.sampling import meas2img2
        # import matplotlib.pyplot as plt

        # Ord = np.ones((64,64))

        # m_plot_pos = meas2img2(hpos_right_order, Ord) 
        # plt.figure()
        # plt.imshow(m_plot_pos[:,:,600])

        # m_plot_neg = meas2img2(hneg_right_order, Ord) 
        # plt.figure()
        # plt.imshow(m_plot_neg[:,:,600])
        

    def RGB_reconstruction(self,datacube,wavelengths):
        """
        RGB_reconstruction allows to extract red, green and blue channels from a datacube
        to create a false RGB image to represent it in the visible spectral range.

        Parameters
        ----------
        datacube : array of floats
            3D image data cube.
        wavelengths : array of floats
            1D sampled spectrometers wavelengths.

        Returns
        -------
        image_rgb : array
            3D array containing red, green and blue channels of the datacube.

        """
        
        idx_blue_low=(np.abs(wavelengths-400)).argmin()
        idx_blue_high=(np.abs(wavelengths-450)).argmin()
        
        idx_green_low=(np.abs(wavelengths-525)).argmin()
        idx_green_high=(np.abs(wavelengths-675)).argmin()
        
        idx_red_low=(np.abs(wavelengths-600)).argmin()
        idx_red_high=(np.abs(wavelengths-650)).argmin()
        
        image_rgb=np.zeros((np.size(datacube,0),np.size(datacube,1),3))

    
        image_rgb[:,:,0]=np.mean(datacube[:,:,idx_red_low:idx_red_high],2)
        image_rgb[:,:,1]=np.mean(datacube[:,:,idx_green_low:idx_green_high],2)
        image_rgb[:,:,2]=np.mean(datacube[:,:,idx_blue_low:idx_blue_high],2)
        
        image_rgb[:,:,0]=255*(image_rgb[:,:,0]-image_rgb[:,:,0].min())/(image_rgb[:,:,0].max()-image_rgb[:,:,0].min())
        image_rgb[:,:,1]=255*(image_rgb[:,:,1]-image_rgb[:,:,1].min())/(image_rgb[:,:,1].max()-image_rgb[:,:,1].min())
        image_rgb[:,:,2]=255*(image_rgb[:,:,2]-image_rgb[:,:,2].min())/(image_rgb[:,:,2].max()-image_rgb[:,:,2].min())
        
        image_rgb=np.uint8(image_rgb)
        
        return image_rgb

    def linear_hadam_spyrit_reconstruct(self):

        h=int(np.sqrt(len(self.onepix_mes["spectra"])/2))
        M = h*h        # number of measurements (here, no compression)
        
        Ord = np.ones((h,h)) 
        meas_op = HadamSplit(M, h, Ord)
        
        prep_op = SplitPoisson(1.0, meas_op) 
        m_noiseless = prep_op(self.spyrit_mes)
        
        recon_op = PseudoInverse()
        z_noiseless = recon_op(m_noiseless, meas_op)
        
        self.datacube = z_noiseless.view(-1,h,h).numpy()
        self.datacube=self.datacube.T
        
        # x = meas_op.inverse(self.spyrit_mes)
        # self.datacube = x.view(-1,h,h).numpy()
        
        
    def cnn32to64_hadam_spyrit_reconstruct(self,device='cpu'):
        chemin_script = os.getcwd()
        Cov_rec = np.load(chemin_script+'\cnn_model\Cov_64x64.npy')
        title=chemin_script+'\cnn_model\cnn_32to64'
        
        
        
        
        
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
        
        
        
        
        
        
        
        
        
            
        
            