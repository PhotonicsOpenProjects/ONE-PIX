import os
import cv2
import numpy as np
from tkinter import *
from tkinter import filedialog
import glob
from tkinter.messagebox import showwarning


class CreationPatterns:
    """Class CustomPatterns allows to create a sequence of loaded patterns and their order list"""

    def __init__(self, spatial_res=0, height=0, width=0):
        self.nb_patterns = 0
        self.patterns_order = []
        self.interp_method = cv2.INTER_AREA

    """
    Inputs: 
        sequence : sequence of patterns to save in jpeg file in dedicated folder 
        pattern_order : list of name of pattern contained in sequence 
        
    Outputs :
        None
    
    """

    def create_folder_sequence(self, sequence, pattern_order, folder_name):
        """
        This function allows to create a folder containing jpeg pictures of all
        patterns contained in a sequence.

        Parameters
        ----------
        sequence : array
            3D array of patterns to be each saved in jpeg file in dedicated folder.
        pattern_order : list
            list of strings name of pattern contained in sequence.
        folder_name : str
            folder path where images are saved.

        Returns
        -------
        None.

        """

        os.mkdir(folder_name)
        os.chdir(folder_name)

        for i in range(0, np.size(sequence, 2)):
            cv2.imwrite(f"{pattern_order[i]}.jpg", 255 * sequence[:, :, i])

        os.chdir("../")

    def sequence_order(self):
        """
        Unused here

        Returns
        -------
        None.

        """
        pass

    def creation_patterns(self):
        """
        This function allows to select a folder containing jpeg image
        of patterns and store them in a sequence.


        Returns
        -------
        None.

        """
        self.patterns = []
        try:
            chemin_script = os.getcwd()
            root = Tk()
            root.withdraw()
            root.attributes("-topmost", 1)
            chemin_mesure = filedialog.askdirectory(
                title="Select the folder containing the patterns to be projected",
                initialdir=chemin_script,
            )
            os.chdir(chemin_mesure)
            # list_nom_mesure = sorted(glob.glob(('*.jpg')),key=os.path.getmtime)
            types = ["*.jpg", "*.png"]
            list_nom_mesure = []
            # list_nom_mesure = sorted(glob.glob(('*.jpg')),key=os.path.getmtime)
            for ext in types:
                this_type_files = sorted(glob.glob(ext), key=os.path.getmtime)
                list_nom_mesure += this_type_files

            for i in range(len(list_nom_mesure)):
                try:
                    self.patterns.append(
                        cv2.cvtColor(cv2.imread(list_nom_mesure[i]), cv2.COLOR_BGR2GRAY)
                        / 255
                    )
                    self.patterns_order.append(list_nom_mesure[i][:-4])
                except cv2.error:
                    pass

            os.chdir(chemin_script)
            self.nb_patterns = len(self.patterns)
            return self.patterns

        except (OSError, TypeError):
            showwarning("Path error", "Undefined folder path")

    def save_raw_data(self, acquisition_class, path=None):
        saver = FIS.FisCommonAcquisition(acquisition_class)
        saver.save_raw_data(path=None)
