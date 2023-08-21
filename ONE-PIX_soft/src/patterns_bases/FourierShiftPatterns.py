import numpy as np

class FourierShiftPatterns:
    """ Class FourierShiftPatterns allows to create a sequence of 
        Fourier shifted patterns and their order list
    """
    def __init__(self,spatial_res):
        self.spatial_res=spatial_res
        if (self.spatial_res%2==0):
            self.spatial_res=self.spatial_res+1
        self.spectrum_size=(self.spatial_res-1)//2
        self.nb_patterns=2*(self.spectrum_size+1)*(2*self.spectrum_size+1)
        self.sequence=[]        


    def sequence_order(self):
        """
        This function allows to create a Fourier patterns sequence with the shifting method.

        Returns
        -------
        pattern_order : list of str
            list of name of fourier patterns stored in sequence. 
            The name contains shifting parameter names (preal or pim) 
            and the associated coordinates from the half rigth spatial spectrum.  
        .
        freqs : list of tuples
            list of tuples of 2D spatial frequencies sampled.

        """
        pattern_order=[]
        freqs=[]
        for j in range(self.spectrum_size+1): #column broom
            for k in range(-self.spectrum_size,self.spectrum_size+1): #line broom
                pattern_order.append("preal(%d,%d)"%(self.spectrum_size+k,j))
                pattern_order.append("pim(%d,%d)"%(self.spectrum_size+k,j))
                freqs.append((j,k))
                
        return pattern_order,freqs
    

    def creation_patterns(self,X,Y,freq):
        """
        Function for the creation of Fourrier patterns with the shifting method

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
        Preal : array
            Real pattern Fourier pattern.
        Pim : array
            Imaginary Fourier pattern.

        """
    
        j,k=freq
        height=np.size(X,0) # heigth in pixel of the desired pattern
        width=np.size(X,1) # width in pixel of the desired pattern
        u=k/height # spatial horizontal frequency
        v=j/width # spatial vertical frequency
        
        A=2*np.pi*X*u 
        B=2*np.pi*Y*v 
        
        Preal=np.cos(A+B,dtype=np.float32) #desired real pattern creation
        Pim=np.sin(A+B,dtype=np.float32) #desired imaginary pattern creation
        
        return Preal,Pim
