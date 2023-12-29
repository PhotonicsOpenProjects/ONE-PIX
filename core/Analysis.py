from core.ImagingMethodBridge import *
import os
import glob
from tkinter import *
from tkinter import filedialog
class Analysis:

    def __init__(self,rec=None):
        
        if rec is None:
            self.load_data()
            self.imaging_method_name=rec["imaging_method"]
            self.reconstructed_image=rec["reconstructed_image"]
            self.wavelengths=rec["wavelengths"]
            
        else:
            self.imaging_method_name=rec.imaging_method_name
            self.reconstructed_image=rec.imaging_method.reconstructed_image
            self.wavelengths=rec.wavelengths
        
        self.imaging_method=ImagingMethodBridge(self.imaging_method_name)
        self.imaging_method.analysis()
        self.analyser= self.imaging_method.image_analysis_method
    
    def read_header(self):
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
        try:
            chemin_script = os.getcwd()
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', 1)
            chemin_mesure = filedialog.askdirectory(title = "Select the folder containing the acquisitions", initialdir = chemin_script)
            os.chdir(chemin_mesure)
        except Exception as e:
            print(e)

        header_filepath=glob.glob('*.txt')[0]
        header=[]
        with open(header_filepath, 'r') as file:
            for line in file.readlines():
                header.append(line.split(':'))
            acq_data=dict()
            acq_data['Acquisition_name']=header[0][0][8:]
            for x in header:
                if x[0].strip()=='Imaging method':
                    acq_data['imaging_method']=x[1].strip()
                
        os.chdir(chemin_script)
        
        return acq_data

   
    def load_data(self):
        self.read_header()
        self.analyser.load_reconstructed_data()
         
    

    def plot_rgb_image(self):
        self.analyser.plot_reconstructed_image(self.reconstructed_image,self.wavelengths) 


