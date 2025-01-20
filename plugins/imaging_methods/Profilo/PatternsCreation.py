import numpy as np
import os
import sys


sys.path.append(f"..{os.sep}")


class CreationPatterns:
    """Class FourierSplitPatterns allows to create a sequence of
    Fourier split patterns and their order list
    """

    def __init__(self, spatial_res, height, width):
        self.height=height
        self.width=width
        pass

    def generate_sinusoidal_pattern(self,frequency, phase_shift, width, height):
   
        x = np.linspace(0, 2 * np.pi, width)
        y = np.linspace(0, 2 * np.pi, height)
        X, Y = np.meshgrid(x, y)
        
        pattern = np.sin(frequency * X + phase_shift) 
        return pattern

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
        freqs=[]
        pattern_order=[]
        for i, pattern in enumerate(self.patterns):
            pattern_order.append(f'pattern{i}')
            freqs.append(str(i))

        return pattern_order, freqs

    def creation_patterns(self):
    
        frequency = 20  # Fréquence des sinus
        # Décalage de phase. 4 premiers : 1e set de patterns, 4 suivants : 2e set de patterns
        phase_shifts = [0, np.pi/2, np.pi,3*
        np.pi/2,np.pi/4, 3*np.pi/4, 5*np.pi/4,7*np.pi/4]
        self.patterns = [self.generate_sinusoidal_pattern(frequency, phase_shift, self.width, self.height) for phase_shift in phase_shifts]
        self.pattern_order=self.sequence_order()
        return self.patterns

    def save_raw_data(self, acquisition_class, path=None):
        pass