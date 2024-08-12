import numpy as np
from scipy.fftpack import dct, idct
from plugins.imaging_methods.FIS_common_functions.FIS_common_reconstruction import (
    FisCommonReconstruction,
)


class Reconstruction:
    """Class to reconstruct a data cube from Fourier splitting ONE-PIX method."""

    def __init__(self, spectra, pattern_order):
        self.spectra = spectra
        self.pattern_order = pattern_order

    def spectrum_reconstruction(self):
        """
        This function allows to reconstruct the half right hyperspectral
        and spatial spectrum of the imaged scene.


        Returns
        -------
        half_spectrum : complex array of floats
            the half rigth hyperspectral and spatial spectrum of the imaged scene.

        """
        coord = []
        x = []
        y = []
        spectre_desplit = (
            self.spectra[0::2, :]
            - self.spectra[1::2, :])
        
        for i in range(0, np.size(self.spectra, 0), 2):
            deb = self.pattern_order[i].find("(")
            coord.append(self.pattern_order[i][deb:])
            coord_split = str.split(coord[-1][1:-1], ",")
            x.append(int(coord_split[0]))
            y.append(int(coord_split[1]))

        x = np.asarray(x)
        y = np.asarray(y)
        spectre_desplit = np.asarray(spectre_desplit)
        # spectre_desplit=self.snr_filt(spectre_desplit)
        half_spectrum = np.zeros(
            (np.max(x) + 1, np.max(y) + 1, np.size(spectre_desplit, 1)),
            dtype=np.float32,
        )

        for i in range(0, np.size(x)):
            half_spectrum[x[i], y[i]] = spectre_desplit[i, :]

        return half_spectrum

    def image_reconstruction(self):
        """
        Function for the reconstruction of the whole Fourier spectrum and the hyperspectral image.

        Returns
        -------
        whole_spectrum : complex array of floats
            whole spatial spectrum of the hyperspectral image (3D array axis0: X spatial frequency axis1:Y spatial frequency axis2: wavelengths) .
        hyperspectral_image : TYPE
            the reconstructed hyperspectral image (3d array :axis0: X spatial dim axis1:vertical spatial dim axis2: wavelengths dimension).

        """

        spectrum = self.spectrum_reconstruction()
        hyperspectral_image=np.zeros_like(spectrum)
        for wl in range(np.shape(spectrum,2)):
            hyperspectral_image[:,:,wl]=idct(idct(spectrum[:,:,wl].T, norm='ortho').T, norm='ortho')

        return hyperspectral_image

    def save_reconstructed_image(
        self, datacube, wavelengths, header, filename, save_path=None
    ):
        saver = FisCommonReconstruction()
        saver.save_acquisition_envi(datacube, wavelengths, header, filename, save_path)
