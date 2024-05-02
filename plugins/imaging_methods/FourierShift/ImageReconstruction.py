from plugins.imaging_methods.FIS_common_functions.FIS_common_reconstruction import (
    FisCommonReconstruction,
)
import numpy as np


class Reconstruction:
    """Class to reconstruct a data cube from Fourier shifting ONE-PIX method."""

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
        spectre_desplit = self.spectra[0::2, :] - 1j * self.spectra[1::2, :]
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
            dtype=np.complex64,
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
            whole spatial spectrum of the hyperspectral image
            (3D array axis0: X spatial frequency axis1:Y spatial frequency axis2: wavelengths) .
        hyperspectral_image : array of floats
            the reconstructed hyperspectral image
            (3d array :axis0: X spatial dim axis1:vertical spatial dim axis2: wavelengths dimension).

        """

        half_spectrum = self.spectrum_reconstruction()
        left_spectrum = np.rot90(
            np.conjugate(half_spectrum[:, 1:, :]), 2
        )  # creation of the half spatial left spectrum by conjugate symmetry
        whole_spectrum = np.concatenate(
            (left_spectrum, half_spectrum), axis=1
        )  # concatenation of the left and right part of the spatial spectrum
        hyperspectral_image = np.abs(
            np.fft.ifftn(whole_spectrum, axes=(0, 1))
        )  # 0 calculation of the hyperspectral image

        return hyperspectral_image

    def save_reconstructed_image(
        self, datacube, wavelengths, header, filename, save_path=None
    ):
        saver = FisCommonReconstruction()
        saver.save_acquisition_envi(datacube, wavelengths, header, filename, save_path)
