import os
import pickle
import numpy as np
import cv2
import plugins.imaging_methods.FIS_common_functions.FIS_common_acquisition as FIS

class CreationPatterns:
    def __init__(self, spatial_res, height, width):
        print("spod is here")
        self.spatial_res=spatial_res
        self.width=width
        self.height=height
        
        if self.spatial_res%2==0:
            self.spatial_res += 1

        self.interp_method=cv2.INTER_LINEAR_EXACT

    def creation_patterns(self):
        patterns = []
        self.patterns_order = []
        for file in os.listdir('../../plugins/imaging_methods/Spod/convolutional_filters_pickle'):
            with open('../../plugins/imaging_methods/Spod/convolutional_filters_pickle/'+file, 'rb') as pklfile:
                mask = mask = pickle.load(pklfile)
                for i in range(mask.shape[0]):
                    patterns.append(np.uint8(255*(mask[i]/np.max(mask[i]))))
                    self.patterns_order.append('nothing')
        return patterns
    
    def sequece_order(self):
        order = self.creation_patterns()
        freqs = [1 for _ in range(len(order))]
        
        return order, freqs
    

    def save_raw_data(self,acquisition_class,path=None):
        saver=FIS.FisCommonAcquisition(acquisition_class)
        saver.save_raw_data(path=None)