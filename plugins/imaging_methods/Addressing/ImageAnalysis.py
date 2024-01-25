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

    
    def data_normalisation(self,data,ref_data):
        # dark pattern correction
        self.spectra-=self.spectra[-1,:]
        self.spectra=self.spectra[:-1,:]
        
        if self.normalisation_path !='':
            try:
                # Load raw data
                acq_data=self.load_reconstructed_data(self.normalisation_path)
                ref_datacube=acq_data['hyperspectral_image']
                masks=np.asarray(self.pattern_lib.decorator.sequence)[:-1,:,:]
                nb_masks=np.size(masks,0)
                print(f"{nb_masks=}")
                new_masks=np.zeros((nb_masks,np.size(ref_datacube,0),np.size(ref_datacube,1)))
                for idx in range(nb_masks):
                    new_masks[idx,:,:]=cv2.resize(masks[idx,:,:],np.shape(new_masks[idx,:,:]),interpolation=cv2.INTER_AREA)


                ref_spec=np.zeros((nb_masks,np.size(ref_datacube,2)))
                for idx in range(nb_masks):
                    mask=np.where(new_masks[idx,:,:],new_masks[idx,:,:],np.nan)/255
                    for wl in range(np.size(ref_datacube,2)):
                        ref_spec[idx,wl]=np.nanmean(ref_datacube[:,:,wl].squeeze()*mask,axis=(0,1))

                ref_spec-=np.repeat(np.nanmean(ref_spec[:,:10],axis=1)[:,np.newaxis],np.size(ref_datacube,2),axis=1)
                
                self.normalised_datacube=self.spectra/ref_spec
            except Exception as e:
                print(e)
        return normalised_data


    def plot_reconstructed_image(self,datacube,wavelengths):
        pass
        









        