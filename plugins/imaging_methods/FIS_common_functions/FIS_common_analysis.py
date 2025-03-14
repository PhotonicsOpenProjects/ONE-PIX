import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import glob
from scipy.signal import savgol_filter
from tkinter import filedialog
from tkinter import *
import cv2
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import spectral.io.envi as envi
from scipy.interpolate import interp1d
from pathlib import Path

class FisAnalysis:

    def __init__(self):
        return

    def get_header_data(self, path):
        """
        This function allows to generate a dictionnary containing acquisition data
        useful for the data cube reconstruction.

        Parameters
        ----------
        path : str
            Header file path

        Returns
        -------
        acq_data : dict
            Dictionnary containing acquisition data.

        """

        header = []
        with open(path, "r") as file:
            for line in file.readlines():
                header.append(line.split(":"))
        acq_data = dict()
        # acq_data['Acquisition_name']=header[0][0][8:]
        for x in header:
            if x[0].strip() == "Imaging method":
                acq_data["imaging_method"] = x[1].strip()

            if x[0].strip() == "Integration time":
                acq_data["integration_time_ms"] = float(x[1].strip()[:-2])

        return acq_data

    def load_hypercube(self, opt=None):
        """
        This function allows to load saved spectra with timers of the displays and spectrometers.
        at runtime, a window appears to select the folder path in which the data are located.

        Returns
        -------
        acq_data : dict
            Dictionary containing data extracted from files saved after acquisition to reconstruct data cubes.

        """

        res = {"reconstructed_image": [], "wavelengths": []}

        if opt == None:
            if os.path.isdir("./Hypercubes"):
                data_folder = "./Hypercubes"
            elif "../Hypercubes":
                data_folder = "../Hypercubes"
            else:
                data_folder = os.getcwd()

            meas_path = filedialog.askdirectory(
                title="Select the folder containing the acquisitions",
                initialdir=data_folder,
            )
        elif opt == "last":
            root_path = os.getcwd()
            path = os.path.join(root_path, "Hypercubes")
            meas_path = max(glob.glob(os.path.join(path, "*/")), key=os.path.getmtime)

        else:
            meas_path = opt

        hyp_filename = glob.glob(f"{meas_path}/*.hdr")[0]
        try:
            info_filename = glob.glob(f"{meas_path}/*.txt")[0]
            res["pattern_method"] = self.get_header_data(info_filename)[
                "imaging_method"
            ]
        except:
            pass
        res["infos"] = "ONE_PIX_analysis" + meas_path.split("/")[-1][19:]
        data = envi.open(hyp_filename)
        res["reconstructed_image"] = data.load()
        res["wavelengths"] = np.array(data.bands.centers)

        return res

    def snr_filt(self, spectre_desplit, noise_level=500):
        """
        snr_filt filters spectra in which the maximum intensity is lower than a defined level.

        Parameters
        ----------
        spectre_desplit : array of floats
            2D array of spectra.
        noise_level : float, optional
            minimum accepted intensity level. The default is 500.

        Returns
        -------
        spectre_desplit : array of floats
            filtered 2D array of spectra.

        """
        M = np.max(abs(spectre_desplit), axis=1)
        idx_noise = np.squeeze(np.array(np.where(M < noise_level)))
        spectre_desplit[idx_noise, :] = 0
        return spectre_desplit

    def Flux2Ref(self, rawHypercube, Wavelengths, reference=None):
        """
        Flux2Ref allows to normalize a raw hypercube in reflectance using a standard present in
        the reconstructed image and its reflectance certificate.

        Parameters
        ----------
        rawHypercube: numpy.array
            3D array of spectral intensities data cube.
        Wavelengths: numpy.array of floats
            1D array of spectrometer's sampled wavelengths.
        reference: numpy.array, optional
            2D array of reflectance certificate composed of wavelengths and reflectance data.
            The default is None for RELATIVE reflectances.

        Returns
        ----------
        Normalised_Hypercube (numpy.array)
            Reflectance normalised hypercube.
        """
        if reference == None:
            reference = np.array([Wavelengths, np.ones_like(Wavelengths)])
        sz = np.shape(rawHypercube)  # Hypercube dimensions
        # Display spectral mean of the hypercube and select the reference area
        fig, ax = plt.subplots(1)
        ax.imshow(np.mean(rawHypercube, axis=2))
        plt.title("Select a reference area to normalise the data cube")
        x1, x2 = plt.ginput(2)  # Select two points to define reference area
        x1 = np.round(x1).astype(np.int32)
        x2 = np.round(x2).astype(np.int32)
        # Create a Rectangle patch
        rect = patches.Rectangle(
            (x1[0], x1[1]),
            x2[0] - x1[0],
            x2[1] - x1[1],
            linewidth=1,
            edgecolor="r",
            facecolor="none",
        )
        ax.add_patch(rect)  # Add the patch to the Axes
        plt.show()
        # Determine the spectral normalization coefficient
        Refmes = np.mean(
            rawHypercube[x1[1] : x2[1], x1[0] : x2[0], :], axis=(0, 1)
        )  # 2D spatial mean of the selected area
        Lref = np.squeeze(
            np.interp(Wavelengths, reference[:, 0], reference[:, 1])
        )  # Interpolation of the reflectance certificate to fit with experimental Wavelengths sampling
        Normcoeff = Lref / Refmes  # Normalisation coefficient

        # Hypercube normalisation without for loops
        RefHypercube = np.tile(
            np.reshape(Normcoeff, [1, 1, sz[2]]), [sz[0], sz[1], 1]
        )  # reshape NormCoeff into a hypercube
        Normalised_Hypercube = rawHypercube * RefHypercube  # Hypercube Normalisation

        return Normalised_Hypercube

    def spikes_correction(self, res):
        """
        Allows to correct by clicking on an over represented frequency in the Fourier domain.

        Parameters
        ----------
        res: dict
            dictionnary of acquisition results. Especially contains the whole spatial spectrum data cube
            and the association image datacube.

        Returns
        -------
        res: dict
            actualised dictionnary of acquisition results.


        """

        fig, ax = plt.subplots()
        whole_spectrum = np.fft.fftshift(
            np.fft.fft2(res["reconstructed_image"], axes=(0, 1))
        )
        plt.imshow(np.log10(abs(np.mean(whole_spectrum, 2))))
        plt.title(
            "Spectral frequencies spikes correction. Pacq_datas escape key to end"
        )
        p = plt.ginput(-1)
        p = np.round(p).astype(np.int32)
        plt.clf()

        for pixel in p:
            if pixel[0] == np.size(whole_spectrum, 1) - 1:
                whole_spectrum[pixel[1], pixel[0], :] = whole_spectrum[
                    pixel[1], pixel[0] - 2, :
                ]
            else:
                whole_spectrum[pixel[1], pixel[0], :] = whole_spectrum[
                    pixel[1], pixel[0] + 1, :
                ]
        plt.imshow(np.log10(abs(np.mean(whole_spectrum, 2))))
        plt.show()
        res["reconstructed_image"] = abs(np.fft.ifft2(whole_spectrum, axes=(0, 1)))
        return res

    def datacube_normalisation_snv(self, datacube):
        """
        datacube_normalisation_snv allows to normamlize an hypercube using Standrad Variate normalisation

        Parameters
        ----------
        datacube : array
            3D image data cube.

        Returns
        -------
        datacube : array
            3D normalize datacube.

        """
        norm_datacube = np.zeros_like(datacube)
        for i in range(0, np.shape(datacube)[0]):
            for j in range(0, np.shape(datacube)[1]):
                norm_datacube[i, j, :] = (
                    datacube[i, j, :] - np.mean(datacube[i, j, :])
                ) / np.std(datacube[i, j, :])
        return norm_datacube

    def datacube_reflectance_normalisation(self, datacube, ref_datacube):
        if np.shape(ref_datacube) != np.shape(datacube):
            ref = np.zeros_like(datacube)
            for wl in range(np.size(ref, 2)):
                ref[:, :, wl] = cv2.resize(ref_datacube[:, :, wl], (np.shape(ref)[:2]))
        else:
            ref = ref_datacube

        normalised_datacube = datacube / ref

        return normalised_datacube

    def select_disp_spectra(self, datacube, wavelengths, n, mode):
        """
        select_disp_spectra allows to select pixel(s) of one hypercube and plot their spectra.

        Parameters
        ----------
        datacube : array of floats
            3D image data cube.
        wavelengths : array of floats
            1D array of sampled wavelengths.
        n : int
            Number of spectra to plot.
        mode : str
            for the mean area of spectra allows to plot mean ('mean') or each
            selected spectrum in one figure ('single').

        Returns
        -------
        spec : array
            Spectra selected by the user from the data cube.

        """
        # Display Hypercube spectral mean to visualise an image
        rgb_image = self.RGB_reconstruction(datacube, wavelengths)
        fig, ax = plt.subplots()
        #     plt.subplot(1,2,1)
        ax.imshow(rgb_image)

        # Selection of pixel(s) or region of interest
        if mode == "single":
            self.tick = np.arange(n) + 1
            # Select pixel(s)
            self.pixels = fig.ginput(n)
            self.pixels = np.round(self.pixels).astype(np.int32)
            # Display results
            plt.plot(self.pixels[:, 0], self.pixels[:, 1], "x", color="red")
            for i, txt in enumerate(self.tick):
                plt.annotate(
                    txt,
                    (self.pixels[i, 0] + 1, self.pixels[i, 1] + 1),
                    color="r",
                    bbox=dict(boxstyle="circle"),
                )
            spec = datacube[self.pixels[:, 1], self.pixels[:, 0], :]
            plt.show(block=False)

        elif mode == "mean":
            # Select 2 corner pixels of rectangle area
            p = plt.ginput(2)
            p = np.round(p).astype(np.int32)
            spec = datacube[
                p[0, 1] : p[1, 1], p[0, 0] : p[1, 0], :
            ]  # 2D spatial mean of the selected area

            # Display results
            rect = patches.Rectangle(
                (p[0, 0], p[0, 1]),
                p[1, 0] - p[0, 0],
                p[1, 1] - p[0, 1],
                linewidth=1,
                edgecolor="r",
                facecolor="none",
            )
            ax.add_patch(rect)  # Add the patch to the Axes
            plt.subplot(1, 2, 2)
            plt.plot(wavelengths, np.mean(spec, axis=(0, 1)))
            plt.xlabel("Wavelengths (nm)")
            plt.ylabel("Mean intensity (counts)")
            plt.show(block=False)

        else:
            print(
                "mode='single' to display each spectrum or mode='mean' to display the mean of the spectra from the selected area"
            )

        plt.close()

        return spec

    def smooth_datacube(self, datacube, window_length, polyorder):
        """
        This function allows to smooth spectra of a whole datacube using Savitzky-Golay filter.
        See more at :
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html

        Parameters
        ----------
        datacube: array of floats
            3D image data cube.
        window_length : int
            The length of the filter window.
        polyorder : int
            The order of the polynomial used to fit the samples.
            polyorder must be less than window_length.

        Returns
        -------
        smoothed_datacube : array
            3D array of smoothed datacube.

        """
        sz = np.shape(datacube)
        smoothed_datacube = np.zeros(sz)
        for line in range(sz[0]):
            for col in range(sz[1]):
                smoothed_datacube[line, col, :] = savgol_filter(
                    datacube[line, col, :], window_length, polyorder
                )

        return smoothed_datacube

    def RGB_reconstruction(self, datacube, wavelengths, gamma=2.2):
        """
        Convertit une image hyperspectrale en une image en espace CIE XYZ et la transforme en sRGB.
        
        :param hsi_image: Image hyperspectrale sous forme (H, W, C)
        :param wavelengths: Tableau des longueurs d'onde correspondant aux C canaux
        :param cie_cmfs: Matrice des fonctions colorimétriques CIE 1931 (λ, X, Y, Z)
        :param gamma: Correction gamma pour l'affichage
        :return: Image RGB en uint8 (H, W, 3)
        """
        # Récupérer le chemin absolu du script en cours d'exécution
        script_dir = Path(__file__).parent  # Dossier où se trouve le script
        cie_file = script_dir / "CIE1931-2deg-XYZ.csv"  # Fichier CMF attendu dans le même dossier

        # Chargement des fonctions colorimétriques CIE 1931
        cie_cmfs = np.loadtxt(cie_file, delimiter=",")

        # Extraction des longueurs d'onde et des fonctions CMF
        cmf_wavelengths, X_cmf, Y_cmf, Z_cmf = cie_cmfs[:, 0], cie_cmfs[:, 1], cie_cmfs[:, 2], cie_cmfs[:, 3]

        # Interpolation des CMFs pour correspondre aux longueurs d'onde de l'image hyperspectrale
        interp_X = interp1d(cmf_wavelengths, X_cmf, kind='linear', bounds_error=False, fill_value=0)
        interp_Y = interp1d(cmf_wavelengths, Y_cmf, kind='linear', bounds_error=False, fill_value=0)
        interp_Z = interp1d(cmf_wavelengths, Z_cmf, kind='linear', bounds_error=False, fill_value=0)

        # Pondération des bandes spectrales par les CMFs
        X = np.sum(datacube * interp_X(wavelengths), axis=-1)
        Y = np.sum(datacube * interp_Y(wavelengths), axis=-1)
        Z = np.sum(datacube * interp_Z(wavelengths), axis=-1)

        # Empiler les canaux pour obtenir une image XYZ
        xyz_image = np.stack([X, Y, Z], axis=-1)

        # Transformation de XYZ vers sRGB (D65 standard)
        M_XYZ_to_sRGB = np.array([[ 3.2406, -1.5372, -0.4986],
                                [-0.9689,  1.8758,  0.0415],
                                [ 0.0557, -0.2040,  1.0570]])
        
        rgb_image = np.dot(xyz_image, M_XYZ_to_sRGB.T)

        # Normalisation et correction gamma
        rgb_image -= rgb_image.min()
        rgb_image /= rgb_image.max()
        rgb_image = np.power(rgb_image, 1 / gamma)

        # Conversion en uint8 pour affichage
        return (rgb_image * 255).astype(np.uint8)



    def clustering(self, datacube, components, n_cluster):
        """
        Clustering function allow to realize classification of the datacube
        using kmeans algorithm on princpal components of the PCA.


        Parameters
        ----------
        datacube : array
            3D image data cube.
        components : int
            number of principal component used for the kmeans clustering.
        n_cluster : int
            number of cluster for the kmeans clustering.

        Returns
        -------
        image_seg : array of int
            2D array of clustered image.

        """

        image_reshape = np.reshape(
            datacube,
            (np.size(datacube, 0) * np.size(datacube, 1), np.size(datacube, 2)),
        )

        pca = PCA(components)
        principalComponents = pca.fit_transform(image_reshape)

        kmeans = KMeans(n_cluster, n_init=10, random_state=0).fit(principalComponents)
        image_seg = np.reshape(
            kmeans.labels_, (np.size(datacube, 0), np.size(datacube, 1))
        )

        return image_seg

    def display_clust_spectra(self, image_seg, datacube, wl):
        """
        display_clust_spectra allows to display mean spectra of each cluster
        of a segmented image.

        Parameters
        ----------
        image_seg : array of int
            2D array of clustered image.
        datacube : array
            3D image data cube.
        wl : array of floats
            1D sampled spectrometers wavelengths.

        Returns
        -------
        spec : array of floats
            spectra of each cluster.

        """
        n_cluster = np.max(image_seg) + 1
        fig, ax = plt.subplots()

        plt.subplot(1, 2, 1)
        plt.imshow(image_seg)
        plt.title("Clustered image")
        legend = []
        spec = []
        mean_spec = np.zeros((n_cluster, len(wl)))
        plt.subplot(1, 2, 2)
        for clust in range(n_cluster):
            idx_clust = np.where(image_seg == clust)
            spec.append(datacube[idx_clust[0], idx_clust[1], :])
            mean_spec[clust, :] = np.mean(spec[clust], 0)
            legend.append(f"Cluster {clust}")
        plt.plot(wl, mean_spec.T)

        plt.title("Mean spectra of the clusters")
        plt.xlabel("Wavelengths (nm)")
        plt.ylabel("Reflectance")
        plt.legend(legend)

        return spec

    def clip_datacube(self, datacube, wavelengths, lower_bound, upper_bound):
        """
        rognage_hyp allows to clip spectral (3rd) dimension of a datacube to
        limit the analyse to the part of the measured spectra of interest.

        Parameters
        ----------
        datacube : array
            3D image data cube.
        wavelengths : array of floats
            1D sampled spectrometers wavelengths.
        lower_bound : int
            lower bound pixel of the associated wavelengths to start.
        upper_bound : int
            upper bound pixel of the associated wavelengths to end.

        Returns
        -------
        datacube_rogn : array
            3D clipped datacube.
        wavelengths_rogn : array
            1D array of clipped wavelengths.

        """

        indice_min = np.abs(wavelengths - lower_bound).argmin()
        indice_max = np.abs(wavelengths - upper_bound).argmin()

        wavelengths_rogn = wavelengths[indice_min:indice_max]
        datacube_rogn = datacube[:, :, indice_min:indice_max]

        return datacube_rogn, wavelengths_rogn

    def py2ms(self,save_gerbil_name, datacube, wavelengths):
        """

        py2ms allows to save ONE-PIX data into Gerbil format http://gerbilvis.org/
        a window appears to select the directory where the hyperspectral data will be saved in gebril format
        Input:
            save_gerbil_name : the name of the saved data into gerbil format (without .txt extension)


        Parameters
        ----------
        save_gerbil_name : str
            the name of the saved data into gerbil format (without .txt extension).
        datacube : array
            datacube to export into Gerbil format.
        wavelengths : array
            Sampled wavelengths associated to the measured datacube.

        Returns
        -------
        None.

        """

        save_path = filedialog.askdirectory(title="Open the save directory")
        maxval = datacube.max()
        minval = datacube.min()
        Range = maxval - minval
        datacube = (datacube + minval) * (255 / Range)

        fid = open(save_path + "\\" + save_gerbil_name + ".txt", "w")
        os.mkdir(save_path + "\\" + save_gerbil_name)
        nz = np.shape(datacube)

        fid.write("{0} {1} \n".format(nz[2], save_gerbil_name + "\\"))

        for i in range(0, nz[2]):
            filename = "{0}_{1}.png".format(save_gerbil_name, i)
            cv2.imwrite(
                save_path + "\\" + save_gerbil_name + "\\" + filename, datacube[:, :, i]
            )
            fid.write("{0} {1}\n".format(filename, wavelengths[i]))

        fid.close()

    def py2envi(self,save_envi_name, datacube, wavelengths, save_path=None):
        """
        py2ms allows to save ONE-PIX data into ENVI format https://www.l3harrisgeospatial.com/docs/enviheaderfiles.html
        metadata can be improved !

        Parameters
        ----------
        save_envi_name : TYPE
            DESCRIPTION.
        datacube : TYPE
            DESCRIPTION.
        wavelengths : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        if save_path == None:
            save_path = filedialog.askdirectory(title="Open the save directory")
        # foldername=save_path+'\\'+save_envi_name
        filename = save_envi_name + ".hdr"
        # os.mkdir(foldername)
        path = os.getcwd()
        os.chdir(save_path)
        envi.save_image(
            filename,
            datacube,
            dtype=np.float32,
            metadata={
                "wavelength": wavelengths,
            },
        )
        os.chdir(path)
