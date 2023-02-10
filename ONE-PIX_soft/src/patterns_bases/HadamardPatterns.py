import numpy as np
from scipy.linalg import hadamard

class HadamardPatterns:
    """ Class HadamardPatterns allows to create a sequence of 
        Hadamard split patterns and their order list.
    """
    def __init__(self,spatial_res):
             
        self.dim=2**(round(np.log2(spatial_res)))
        self.nb_patterns=2*self.dim**2
        self.sequence=[]
        self.pattern_order=[]
        
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
        pattern_order=[]
        freqs=[]
        
        for j in range(self.dim): #column broom
            for k in range(self.dim): #line broom
                pattern_order.append("Hpos(%d,%d)"%(j,k))
                pattern_order.append("Hneg(%d,%d)"%(j,k))
        freqs.append(1)
                
        return pattern_order,freqs
     


    def creation_patterns(self):
        """
        Function for the creation of Hadamard patterns with the splitting method


        Returns
        -------
        split_patterns : array of int
            3D array of split Hadamard patterns.

        """
        
        hadamard_matrix=hadamard(self.dim**2) # initialized an dim by dim Hadamard matrix
        patterns=np.zeros([self.dim,self.dim,self.dim**2])   # 3D Patterns initialization with zeros values
        for col in range(self.dim**2):
            patterns[:,:,col]=np.reshape(hadamard_matrix[:,col],[self.dim,self.dim]) # reshape of the Patterns in 2D(dim X dim) 
        
        split_patterns=np.zeros((self.dim,self.dim,2*self.dim**2),np.uint8)
        split_patterns[:,:,0::2]=np.uint8((1+patterns)/2)*255
        split_patterns[:,:,1::2]=np.uint8((1-patterns)/2)*255
        split_patterns=[ np.squeeze(x) for x in np.split(split_patterns,2*self.dim**2,axis=2)]
        self.sequence=split_patterns
        self.pattern_order,freqs=self.sequence_order()
        return self.pattern_order,freqs
