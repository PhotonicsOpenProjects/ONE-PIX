import os
import numpy as np
from tkinter import filedialog
from datetime import date
import time
import spectral.io.envi as envi
import cv2
from scipy.interpolate import interp1d
from pathlib import Path


class FisCommonReconstruction:
    def __init__(self, acquisition_dict=None):
        self.acquisition_dict = acquisition_dict
        return
    
    def get_result_to_plot(self, datacube, wavelengths, gamma=2.2):
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


    def save_acquisition_envi(
        self, reconstruction_results, header, save_envi_name=None, save_path=None
    ):
        """
        This function allow to save the resulting acquisitions from one
        OPConfig object into the Hypercube folder.

        Parameters
        ----------
        config : class
            OPConfig class object.

        Returns
        -------
        None.

        """
        datacube=reconstruction_results["reconstructed_data"]
        wavelengths=reconstruction_results["wavelengths"]
        if save_path==None:
            save_path = Path(__file__).resolve().parent.parent.parent.parent / "measure"
            print("save path: ",save_path)
            if os.path.isdir(save_path):
                pass
            else :
                os.mkdir(save_path)

        self.fdate = date.today().strftime(
            "%d_%m_%Y"
        )  # convert the current date in string
        self.actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = (
            f"ONE-PIX_reconstructed_data_{self.fdate}_{self.actual_time}"
            if save_envi_name is None
            else save_envi_name
        )
        
        self.final_path = os.path.join(save_path,folder_name)
        os.mkdir(os.path.join(self.final_path))
        if save_envi_name is None:
            save_envi_name = folder_name
        # saving the acquired spatial spectra hypercube
        self.py2envi(datacube, wavelengths, save_envi_name, self.final_path)
        with open(os.path.join(self.final_path,folder_name) + ".txt", "w+") as header_file:
            header_file.write(header)



    def py2envi(self, datacube, wavelengths, save_envi_name="cube", save_path=None):
        """
        Sauvegarde un cube hyperspectral au format ENVI dans un dossier 'measure'
        situé à la racine du dossier 'onepix_dev' (3 niveaux au-dessus de plugins/).

        Exemple :
        onepix_dev/
        ├── plugins/
        │   └── imaging_methods/
        │       └── FIS_common_functions/
        │           └── FIS_common_reconstruction.py  ← ce script
        └── measure/
            └── cube_xxx/
                ├── cube_xxx.hdr
                ├── cube_xxx.dat
        """
        
        # 🧠 Si wavelengths est un seul nombre, le transformer en liste
        if isinstance(wavelengths, (int, float)):
            wavelengths = [wavelengths]

        # 📁 Dossier du script actuel
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 📁 On remonte 4 niveaux pour atteindre onepix_dev/
        repo_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
        
        # 📁 Crée (si besoin) le dossier measure/ dans onepix_dev/
        measure_dir = os.path.join(repo_root, "measure")
        os.makedirs(measure_dir, exist_ok=True)
        
        # 📁 Si aucun chemin spécifique n’est donné, on crée un sous-dossier
        if save_path is None:
            if not save_envi_name:
                save_envi_name = f"cube_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            save_path = os.path.join(measure_dir, save_envi_name)
        
        os.makedirs(save_path, exist_ok=True)
        
        # 📝 Nom complet du fichier HDR
        hdr_path = os.path.join(save_path, save_envi_name + ".hdr")
        
        # 💾 Sauvegarde du cube ENVI
        envi.save_image(
            hdr_path,
            datacube,
            dtype=np.float32,
            metadata={"wavelength": list(map(str, wavelengths))}
        )
        
        print(f"[OK] Cube ENVI sauvegardé dans : {save_path}")
        print(f"    - Fichier HDR : {hdr_path}")
        
        # 🔁 Retourne le chemin pour d'autres usages
        return save_path

    def py2ms(self, datacube, wavelengths, save_gerbil_name):
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
