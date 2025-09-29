import numpy as np
from plugins.imaging_methods.FIS_common_functions.FIS_common_reconstruction import (
    FisCommonReconstruction,
)


class Reconstruction:
    """Class to reconstruct a data cube from Fourier splitting ONE-PIX method."""

    def __init__(self,acquisition_dict):
        self.reconstruction_results={}
        self.reconstruction_results["wavelengths"]=acquisition_dict["wavelengths"]
        self.spectra = np.asarray(acquisition_dict["spectra"])
        self.wavelengths=np.asarray(acquisition_dict["wavelengths"])
        self.pattern_order = acquisition_dict["patterns_order"]
        self.fis=FisCommonReconstruction()

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
            self.spectra[0::4, :]
            - self.spectra[1::4, :]
            - 1j * (self.spectra[2::4, :] - self.spectra[3::4, :])
        )
        for i in range(0, np.size(self.spectra, 0), 4):
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
            whole spatial spectrum of the hyperspectral image (3D array axis0: X spatial frequency axis1:Y spatial frequency axis2: wavelengths) .
        hyperspectral_image : TYPE
            the reconstructed hyperspectral image (3d array :axis0: X spatial dim axis1:vertical spatial dim axis2: wavelengths dimension).

        """

        half_spectrum = self.spectrum_reconstruction()
        left_spectrum = np.rot90(
            np.conjugate(half_spectrum[:, 1:, :]), 2
        )  # creation of the half spatial left spectrum by conjugate symmetry
        whole_spectrum = np.concatenate(
            (left_spectrum, half_spectrum), axis=1
        )  # concatenation of the left and right part of the spatial spectrum
        self.hyperspectral_image = np.abs(
            np.fft.ifftn(whole_spectrum, axes=(0, 1))
        )  # 0 calculation of the hyperspectral image
        self.reconstruction_results["reconstructed_data"]=self.hyperspectral_image

        return  self.hyperspectral_image
    
    def get_result_to_plot(self):
        self.result_to_plot=self.fis.get_result_to_plot(self.hyperspectral_image,self.wavelengths)
        self.reconstruction_results["result2plot"]=self.result_to_plot
        return  self.result_to_plot
        

    def save_reconstructed_image(
        self, header, filename, save_path=None
    ):
        self.fis.save_acquisition_envi(self.reconstruction_results, header, filename, save_path)
