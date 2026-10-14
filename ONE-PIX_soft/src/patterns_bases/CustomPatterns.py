import os
import cv2
import numpy as np
from tkinter import *
from tkinter import filedialog
import glob

class CustomPatterns:
    """ Class CustomPatterns allows to create a sequence of loaded patterns and their order list"""
    def __init__(self,spatial_res):
        self.nb_patterns=0
        self.sequence=[]
        self.pattern_order=[]
    
    """
    Inputs: 
        sequence : sequence of patterns to save in jpeg file in dedicated folder 
        pattern_order : list of name of pattern contained in sequence 
        
    Outputs :
        None
    
    """
    def create_folder_sequence(self,sequence,pattern_order,folder_name):
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
        
        for i in range(0,np.size(sequence,2)):
            cv2.imwrite(f"{pattern_order[i]}.jpg",255*sequence[:,:,i])
         
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
        chemin_script = os.getcwd()
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', 1)
        chemin_mesure = filedialog.askdirectory(title = "Select the folder containing the patterns to be projected", initialdir = chemin_script)
        os.chdir(chemin_mesure)
        # list_nom_mesure = sorted(glob.glob(('*.jpg')),key=os.path.getmtime)
        types = ["*.jpg", "*.png"]
        list_nom_mesure=[]
        # list_nom_mesure = sorted(glob.glob(('*.jpg')),key=os.path.getmtime)
        for ext in types:
            this_type_files = sorted(glob.glob(ext),key=os.path.getmtime)
            list_nom_mesure += this_type_files
        
        for i in range(len(list_nom_mesure)):
            try:
                self.sequence.append(cv2.cvtColor(cv2.imread(list_nom_mesure[i]), cv2.COLOR_BGR2GRAY)/255)
                self.pattern_order.append(list_nom_mesure[i][:-4])
            except cv2.error:
                pass
            
        os.chdir(chemin_script)
        self.nb_patterns=len(self.sequence)
        return self.pattern_order,[]
