import numpy as np
from src.patterns_bases.FourierShiftPatterns import FourierShiftPatterns

class FourierSplitPatterns:
    """ Class FourierSplitPatterns allows to create a sequence of 
        Fourier split patterns and their order list
    """
    def __init__(self,spatial_res):
        self.spatial_res=spatial_res
        if (self.spatial_res%2==0):
            self.spatial_res=self.spatial_res+1
        self.spectrum_size=(self.spatial_res-1)//2
        self.nb_patterns=4*(self.spectrum_size+1)*(2*self.spectrum_size+1)
        self.sequence=[]

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
    

    def creation_patterns(self,X,Y,freq):
        """
        Function for the creation of Fourrier patterns with the splitting method

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
        Preal,Pim=FourierShiftPatterns.creation_patterns(self,X,Y,freq)
        
        #Real positive pattern creation
        pos_r=Preal.copy()
        pos_r[pos_r<0]=0
        pos_r=np.uint8(255*pos_r)
              
        #Real negative pattern creation
        neg_r=Preal.copy()
        neg_r[neg_r>0]=0
        neg_r=np.uint8(255*np.abs(neg_r))
        
        #Imaginary positive pattern creation
        pos_im=Pim.copy()
        pos_im[pos_im<0]=0
        pos_im=np.uint8(255*pos_im)
        
        #Imaginary negative pattern creation
        neg_im=Pim.copy()
        neg_im[neg_im>0]=0
        neg_im=np.uint8(255*np.abs(neg_im))
       
        return pos_r, neg_r, pos_im, neg_im
