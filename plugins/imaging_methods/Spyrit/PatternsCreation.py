import numpy as np
from plugins.imaging_methods.Spyrit.custom_walsh_hadamard import *
import cv2
import plugins.imaging_methods.FIS_common_functions.FIS_common_acquisition as FIS

class CreationPatterns:
    """ Class HadamardPatterns allows to create a sequence of 
        Hadamard split patterns and their order list.
    """
    def __init__(self,spatial_res,height=0,width=0):
             
        self.dim=2**(round(np.log2(spatial_res)))
        self.nb_patterns=2*self.dim**2
        self.sequence=[]
        self.pattern_order=[]
        self.white_pattern_idx=0
        self.interp_method=cv2.INTER_AREA
        if self.dim != spatial_res:
            print(f'Warning: Hadamard sampling request for powers of 2 dimensions. The nearest eligible size is {self.dim}. ')
  
    
    def sequence_order(self):
        """
        This function creates the sequence order list associated to the frequencies displayed

        Returns
        -------
        pattern_order : list of str
            list of name of Hadamard split patterns stored in sequence. 
        freqs : list of tuples
            list of tuples of 2D spatial frequencies sampled.

        """
        patterns_order=[]
        freqs=[]
        
        for j in range(self.dim): #column broom
            for k in range(self.dim): #line broom
                patterns_order.append("Hpos(%d,%d)"%(j,k))
                patterns_order.append("Hneg(%d,%d)"%(j,k))
        freqs.append((j,k))
                
        return patterns_order,freqs
     


    def creation_patterns(self):
        """
        Function for the creation of Hadamard patterns with the splitting method


        Returns
        -------
        split_patterns : array of int
            3D array of split Hadamard patterns.

        """
        
        had_walsh_matrix=np.int8(walsh2_matrix(self.dim)) # initialized an dim by dim Walsh Hadamard matrix
        self.sequence=[]
        for col in range(self.dim**2):
            self.sequence.append(np.uint8(255*((1+(np.reshape(had_walsh_matrix[:,col],[self.dim,self.dim])))//2))) # reshape of the Patterns in 2D(dim X dim)
            self.sequence.append(np.uint8(255*((1-(np.reshape(had_walsh_matrix[:,col],[self.dim,self.dim])))//2)))
        del had_walsh_matrix
        
        self.patterns_order,freqs=self.sequence_order()
        return self.sequence

    def save_raw_data(self,acquisition_class,path=None):
        saver=FIS.FisCommonAcquisition(acquisition_class)
        saver.save_raw_data(path=None)
