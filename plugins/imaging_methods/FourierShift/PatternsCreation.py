import numpy as np

class CreationPatterns:
    """ Class FourierShiftPatterns allows to create a sequence of 
        Fourier shifted patterns and their order list
    """
    def __init__(self,spatial_res,height,width):
        self.spatial_res=spatial_res
        if (self.spatial_res%2==0):
            self.spatial_res=self.spatial_res+1
        self.spectrum_size=(self.spatial_res-1)//2
        self.nb_patterns=2*(self.spectrum_size+1)*(2*self.spectrum_size+1)
        self.white_pattern_idx=2*self.spectrum_size
        self.sequence=[]
        self.width=width
        self.height=height
        y = list(range(self.height))  # horizontal vector for the pattern creation
        x = list(range(self.width))  # vertical vector for the pattern creation
        self.Y, self.X = np.meshgrid(x, y)  # horizontal and vertical array for the pattern creation


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
    

    def creation_freq_patterns(self,freq):
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
        u=k/self.height # spatial horizontal frequency
        v=j/self.width # spatial vertical frequency
        
        A=2*np.pi*self.X*u 
        B=2*np.pi*self.Y*v 
        
        Preal=np.cos(A+B,dtype=np.float32) #desired real pattern creation
        Pim=np.sin(A+B,dtype=np.float32) #desired imaginary pattern creation
        
        return Preal,Pim
    
    def creation_patterns(self):
        self.patterns_order, freqs = self.sequence_order()
        patterns = []

        for freq in freqs:
            patterns.extend(self.creation_freq_patterns(freq))

        return patterns
