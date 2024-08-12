import numpy as np
import os
import sys

sys.path.append(f"..{os.sep}")
from plugins.imaging_methods.FourierShift import PatternsCreation as shift
import cv2
import plugins.imaging_methods.FIS_common_functions.FIS_common_acquisition as FIS


class CreationPatterns:
    """Class FourierSplitPatterns allows to create a sequence of
    Fourier split patterns and their order list
    """

    def __init__(self, spatial_res, height, width):
        # import users defined spatial infos
        self.spatial_res = spatial_res
        self.height = height
        self.width = width

        
        self.nb_patterns = self.spatial_res**2
        # define white pattern index for display
        self.white_pattern_idx = 4 * self.spectrum_size

        self.fourier_shift = shift.CreationPatterns(
            self.spatial_res, self.height, self.width
        )
        self.interp_method = cv2.INTER_LINEAR_EXACT

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
        pattern_order = []
        freqs = []
        for j in range(0, self.spectrum_size + 1):  # column broom
            for k in range(-self.spectrum_size, self.spectrum_size + 1):  # line broom
                pattern_order.append("posr(%d,%d)" % (self.spectrum_size + k, j))
                pattern_order.append("negr(%d,%d)" % (self.spectrum_size + k, j))
                
                freqs.append((j, k))
        return pattern_order, freqs

    def dct_basis_vector(self, k):
        basis_vector = np.cos(np.pi * k * (2 * np.arange(self.spatial_res) + 1) / (2 * self.spatial_res))
        if k == 0:
            basis_vector *= 1 / np.sqrt(self.spatial_res)
        else:
            basis_vector *= np.sqrt(2 / self.spatial_res)
        return basis_vector

    def creation_freq_patterns(self, freq):
        """
        Function for the creation of split Fourrier patterns with the splitting method for one given frequency

        Parameters
        ----------

        """
        u,v=freq
        pattern = np.outer(self.dct_basis_vector(self.spatial_res, u), self.dct_basis_vector(self.spatial_res, v))
        pos=pattern[pattern>=0]
        neg=pattern[pattern<=0]
        return pos,neg

    def creation_patterns(self):
        self.patterns_order, freqs = self.sequence_order()
        patterns = []

        for freq in freqs:
            patterns.extend(self.creation_freq_patterns(freq))

        return patterns

    def save_raw_data(self, acquisition_class, path=None):
        saver = FIS.FisCommonAcquisition(acquisition_class)
        saver.save_raw_data(path=None)
