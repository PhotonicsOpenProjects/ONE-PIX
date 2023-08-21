import numpy as np
import gc
class DFTPatterns:
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
    

    def creation_patterns(self):
        """
        Function for the creation of Hadamard patterns with the splitting method


        Returns
        -------
        split_patterns : array of int
            3D array of split Hadamard patterns.

        """
        nb_freq=(self.spatial_res//2+1)*self.spatial_res
        dft_matrix = np.fft.fftshift(np.complex64((np.fft.fft(np.eye(self.spatial_res**2,dtype=np.uint8))))) 
        
        self.sequence=[]
        idx=np.arange(len(dft_matrix)-nb_freq,len(dft_matrix),1)
        for pattern_id in range(nb_freq):
            pattern=dft_matrix[:,idx[pattern_id]]
            #Reshaping paterns
            preal=np.reshape(np.real(pattern),(self.spatial_res,self.spatial_res),order='C')
            pim=np.reshape(np.imag(pattern),(self.spatial_res,self.spatial_res),order='C')
            # Splitting patterns to display positive images
            self.sequence.append(np.uint8(255*np.where(preal< 0, abs(preal), 0)))
            self.sequence.append(np.uint8(255*np.where(preal> 0, preal, 0)))
            self.sequence.append(np.uint8(255*np.where(pim< 0, abs(pim), 0)))
            self.sequence.append(np.uint8(255*np.where(pim> 0, pim, 0)))
            
        
        del dft_matrix
        gc.collect()
        
        self.pattern_order,freqs=self.sequence_order()
        return self.pattern_order,freqs
