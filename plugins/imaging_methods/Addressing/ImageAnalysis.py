import numpy as np
import matplotlib.pyplot as plt
import os
import cv2

class Analysis:
    """ Class to reconstruct a data cube from Fourier splitting ONE-PIX method."""
    
    def __init__(self,data_path=None):
        self.data_path=data_path
        
   
    
    def load_reconstructed_data(self,):
        try:
            self.reconstructed_data=np.load(['/'.join([self.data_path, files]) for files in os.listdir(self.data_path) if files.startswith('spectra_')][0])
            self.patterns_order=np.load(['/'.join([self.data_path, files]) for files in os.listdir(self.data_path) if files.startswith('patterns_order')][0])
            self.clusters= np.uint8(np.load(['/'.join([self.data_path, files]) for files in os.listdir(self.data_path) if files.startswith('masks')][0]))
            self.wavelengths=np.load(['/'.join([self.data_path, files]) for files in os.listdir(self.data_path) if files.startswith('wavelengths')][0])
            self.rgb_image=cv2.imread(['/'.join([self.data_path, files]) for files in os.listdir(self.data_path) if files.startswith('RGB_cor')][0])
        except Exception as e:
            print(e)

    
    def data_normalisation(self,ref_data):
        
        try:
            nb_clusters=np.size(self.masks,0)
            print(f"{nb_clusters=}")
            new_masks=np.zeros((nb_clusters,np.size(ref_data,0),np.size(ref_data,1)))
            for idx in range(nb_clusters):
                new_masks[idx,:,:]=cv2.resize(self.clusters[idx,:,:],np.shape(new_masks[idx,:,:]),interpolation=cv2.INTER_AREA)


            ref_spec=np.zeros((nb_clusters,np.size(ref_data,2)))
            for idx in range(nb_clusters):
                mask=np.where(new_masks[idx,:,:],new_masks[idx,:,:],np.nan)/255
                for wl in range(np.size(ref_data,2)):
                    ref_spec[idx,wl]=np.nanmean(ref_data[:,:,wl].squeeze()*mask,axis=(0,1))

            ref_spec-=np.repeat(np.nanmean(ref_spec[:,:10],axis=1)[:,np.newaxis],np.size(ref_data,2),axis=1)
            
            self.normalised_data=self.spectra/ref_spec
        except Exception as e:
            print(e)
        


    def plot_reconstructed_image(self,datacube,wavelengths):
        pass
        









        