import numpy as np 

class BlackAndWhitePatterns:
    """ Class BlackAndWhitePatterns allows to create B&W patterns and their order list"""
    
    def __init__(self,nb_patterns,height,width):
        """

        Parameters
        ----------
        nb_patterns : int
            number of patterns to create.
        height : int
            height of the patterns in pixel number.
        width : int
            width of the patterns in pixel number.

        Returns
        -------
        None.

        """
        self.nb_patterns=nb_patterns
        self.height=height
        self.width=width
        self.pattern_order=[]
        self.sequence=[]
        
    def sequence_order(self):
        """
        sequence_order allows to create a list of the names of the created patterns.

        Returns
        -------
        pattern_order : list
            list of names of patterns stored in sequence. names containing white or black and the corresponding chronological positionin the sequence.

        """
        
        pattern=0
        while pattern<self.nb_patterns:
            self.pattern_order.append("white_%d"%pattern)
            pattern+=1
            self.pattern_order.append("black_%d"%pattern)
            pattern+=1
        
        return self.pattern_order
    
  
    def creation_sequence(self):
        """
        This function allows to create a sequence containing alternate white and black patterns

        Returns
        -------
        sequence :array of int
            sequence of black and white patterns stored in a 3D numpy array.

        """
   
        self.sequence=np.zeros((self.height,self.width,self.nb_patterns),dtype=np.float32)
        self.sequence[:,:,0::2]=1
        self.sequence=np.split(self.sequence,self.nb_patterns,axis=2)
        
        return self.sequence
