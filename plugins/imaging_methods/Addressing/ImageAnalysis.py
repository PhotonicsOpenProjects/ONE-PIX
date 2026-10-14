import numpy as np
import matplotlib.pyplot as plt
import os
import cv2


class Analysis:
    """Class to reconstruct a data cube from Fourier splitting ONE-PIX method."""

    def __init__(self, data_path=None):
        self.data_path = data_path

    def load_reconstructed_data(self, data_path=None):
        if data_path is None:
            data_path = self.data_path
        try:
            self.reconstructed_data = np.load(
                [
                    "/".join([data_path, files])
                    for files in os.listdir(data_path)
                    if files.startswith("spectra_")
                ][0]
            )
            self.patterns_order = np.load(
                [
                    "/".join([data_path, files])
                    for files in os.listdir(data_path)
                    if files.startswith("patterns_order")
                ][0]
            )
            self.clusters = np.uint8(
                np.load(
                    [
                        "/".join([data_path, files])
                        for files in os.listdir(data_path)
                        if files.startswith("masks")
                    ][0]
                )
            )
            self.wavelengths = np.load(
                [
                    "/".join([data_path, files])
                    for files in os.listdir(data_path)
                    if files.startswith("wavelengths")
                ][0]
            )
            self.rgb_image = cv2.imread(
                [
                    "/".join([data_path, files])
                    for files in os.listdir(data_path)
                    if files.startswith("RGB_cor")
                ][0]
            )
        except Exception as e:
            print(e)

      

    def data_normalisation(self, ref_data,data=None):
        """
        Normalise les données en fonction d'une référence donnée.

        :param ref_data: Cube de données de référence (dimensions [x, y, wl]).
        """
        try:
            # Vérification des dimensions
            ref_height, ref_width, ref_depth = ref_data.shape
            if self.reconstructed_data.shape[1] != ref_depth:
                raise ValueError(
                    f"Les dimensions des longueurs d'ondes ne correspondent pas : "
                    f"ref_data a {ref_depth} longueurs d'onde, "
                    f"mais reconstructed_data en a {self.reconstructed_data.shape[1]}."
                )

            # Nombre de clusters
            nb_clusters = self.clusters.shape[0]
            # Exclure le dernier cluster (par exemple, pour le fond ou le "dark cluster")
            masks_idx = list(range(nb_clusters - 1))


            # Interpolation des clusters vers les dimensions spatiales du cube de référence
            new_masks = np.zeros((len(masks_idx), ref_height, ref_width))

            for i, idx in enumerate(masks_idx):
                new_masks[i, :, :] = cv2.resize(
                    self.clusters[idx, :, :],
                    (ref_width, ref_height),
                    interpolation=cv2.INTER_AREA,
                )

            # Calcul des spectres moyens pondérés par les masques
            ref_spec = np.zeros((len(masks_idx), ref_depth))

            for i, mask in enumerate(new_masks):
                # Normalisation du masque entre 0 et 1
                normalized_mask = np.where(mask > 0, mask / 255, np.nan)

                # Calcul du spectre moyen pour chaque longueur d'onde
                ref_spec[i, :] = np.nanmean(
                    ref_data * normalized_mask[..., np.newaxis], axis=(0, 1)
                )
            
            # Normalisation des données reconstruite avec les spectres de référence
            self.normalised_data =(self.reconstructed_data) / (ref_spec)
            
        except Exception as e:
            print(f"Erreur dans data_normalisation : {e}")
            raise


        

    def plot_reconstructed_image(self, datacube, wavelengths):
        pass
