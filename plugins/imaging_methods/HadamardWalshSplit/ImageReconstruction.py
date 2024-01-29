import numpy as np
from plugins.imaging_methods.HadamardWalshSplit.custom_walsh_hadamard import *
from plugins.imaging_methods.FIS_common_functions.FIS_common_reconstruction import FisCommonReconstruction

class Reconstruction:
    """ Class to reconstruct a data cube from Walsh Hadamard splitting ONE-PIX method."""
    def __init__(self,spectra,pattern_order):
        self.spectra=spectra
        self.pattern_order=pattern_order
        
     
    def spectrum_reconstruction(self):
        """
        This function allows to reconstruct the half rigth hyperspectral and 
        spatial spectrum of the imaged scene with the Walsh Hadamard method

        Returns
        -------
        whole_spectrum : array of floats
            Walsh Hadamard spatial and spectral spectrum of the imaged scene.

        """

     
        spectre_desplit=[]
        coord=[]  
        x=[]
        y=[]
        
        for i in range(0,np.size(self.spectra,0),2):
            spectre_desplit.append(self.spectra[i,:]-self.spectra[i+1,:])
            deb=self.pattern_order[i].find('(')
            coord.append(self.pattern_order[i][deb:])
            coord_split=str.split(coord[-1][1:-1],',')
            x.append(int(coord_split[0]))
            y.append(int(coord_split[1]))
    
        x=np.asarray(x)
        y=np.asarray(y)     
        spectre_desplit=np.asarray(spectre_desplit)
        
        whole_spectrum=np.zeros((np.max(x)+1,np.max(y)+1,np.size(spectre_desplit,1)),dtype=np.float32)
        
        for i in range(0,np.size(x)):
            whole_spectrum[x[i],y[i]]=spectre_desplit[i,:]
    
        return whole_spectrum
 

    def image_reconstruction(self):
        """
        Function for the reconstruction of the whole Walsh Hadamard spectrum and the 
        associated hyperspectral image
        
        Returns
        -------
        whole_spectrum : array of floats
            the whole spatial spectrum of the hyperspectral image 
            (3D array axis0: X spatial frequency axis1:Y spatial frequency axis2: wavelengths).
        hyperspectral_image : array of floats
            the reconstructed hyperspectral image 
            (3d array :axis0: X spatial dim axis1:vertical spatial dim axis2: wavelengths dimension).

        """
        whole_spectrum=self.spectrum_reconstruction()
        dim=np.size(whole_spectrum,0)
        H=walsh_matrix(dim)
        hyperspectral_image=np.zeros_like(whole_spectrum)
        for wl in range(np.size(whole_spectrum,2)): hyperspectral_image[:,:,wl]=abs(H@whole_spectrum[:,:,wl]@H)
        
        return hyperspectral_image

    def save_reconstructed_image(self,datacube,wavelengths,header,filename,save_path=None):
        saver=FisCommonReconstruction()
        saver.save_acquisition_envi(datacube,wavelengths,header,filename,save_path)