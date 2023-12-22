import numpy as np
import os
import sys
sys.path.append(f'..{os.sep}')
from plugins.imaging_methods.FourierShift import PatternsCreation as shift
import cv2

class CreationPatterns:
    """ Class FourierSplitPatterns allows to create a sequence of 
        Fourier split patterns and their order list
    """
    def __init__(self,spatial_res,height,width):
        # import users defined spatial infos
        self.spatial_res=spatial_res
        self.height=height
        self.width=width

        # check if spatial res is an odd number
        if (self.spatial_res%2==0):
            self.spatial_res=self.spatial_res+1
        # half spectrum size definition
        self.spectrum_size=(self.spatial_res-1)//2
        self.nb_patterns=4*(self.spectrum_size+1)*(2*self.spectrum_size+1)
        # define white pattern index for display 
        self.white_pattern_idx=4*self.spectrum_size
        
        self.fourier_shift=shift.CreationPatterns(self.spatial_res,self.height,self.width)
        self.interp_method=cv2.INTER_LINEAR_EXACT

    def sequence_order(self):
        """
        This function allows to create a Fourier patterns sequence with the splitting method.

        Returns
        -------
        pattern_order : list of str
            list of name of fourier patterns stored in sequence. 
            The name contains spliting parameter names (posr negr posim or negim) 
            and the associated coordinates from the half rigth spatial spectrum.
        freqs : list of tuples
            list of tuples of 2D spatial frequencies sampled.

        """
        pattern_order=[]
        freqs=[]
        for j in range(0,self.spectrum_size+1): #column broom
            for k in range(-self.spectrum_size,self.spectrum_size+1): #line broom
                pattern_order.append("posr(%d,%d)"%(self.spectrum_size+k,j))
                pattern_order.append("negr(%d,%d)"%(self.spectrum_size+k,j))
                pattern_order.append("posim(%d,%d)"%(self.spectrum_size+k,j))
                pattern_order.append("negim(%d,%d)"%(self.spectrum_size+k,j))
                freqs.append((j,k))
        return pattern_order,freqs
    

    def creation_freq_patterns(self,freq):
        """
        Function for the creation of split Fourrier patterns with the splitting method for one given frequency

        Parameters
        ----------
        X : array of int
            mesh matrix for the X axis.
        Y : array of int
            mesh matrix for the Y axis.
        freq : tuple
            tuple for spatial frequencies of the current pattern .

        Returns
        -------
        pos_r : array of floats
            Real positive pattern.
        neg_r : array of floats
            Real negative pattern.
        pos_im : array of floats
            Imaginary positive pattern.
        neg_im : array of floats
            Imaginary negative pattern.

        """
        #Create shifted patterns to split them
        preal,pim=self.fourier_shift.creation_freq_patterns(freq)
        
        # Splitting patterns to display positive images

        #Real positive pattern creation
        pos_r=np.uint8(255*np.where(preal> 0, preal, 0))
              
        #Real negative pattern creation
        neg_r=np.uint8(255*np.where(preal< 0, abs(preal), 0))
        
        
        #Imaginary positive pattern creation
        pos_im= np.uint8(255*np.where(pim> 0, pim, 0))
        
        #Imaginary negative pattern creation
        neg_im=np.uint8(255*np.where(pim< 0, abs(pim), 0))
       
       
        return pos_r, neg_r, pos_im, neg_im

    def creation_patterns(self):
        self.patterns_order, freqs = self.sequence_order()
        patterns = []

        for freq in freqs:
            patterns.extend(self.creation_freq_patterns(freq))

        return patterns

        