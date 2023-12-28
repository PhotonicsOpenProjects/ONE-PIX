import numpy as np
from plugins.imaging_methods.FIS_common_functions.FIS_common_analysis import FisAnalysis
class Analysis:
    """ Class to reconstruct a data cube from Fourier splitting ONE-PIX method."""
    
    def __init__(self,data_path):
        self.data_path=data_path
        self.analyse=FisAnalysis()
        return
   
    
    def load_reconstructed_data(self,):
        self.data_dict=self.analyse.load_hypercube(self.data_path)








        