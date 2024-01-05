from core.ImagingMethodBridge import *
import os
import glob
from tkinter import *
from tkinter import filedialog
class Analysis:
    def __init__(self,rec=None,data_path=None):
        self.data_path=data_path
        if rec is None:
            self.read_header()
            self.imaging_method=ImagingMethodBridge(self.imaging_method_name)
            self.imaging_method.analysis(self.data_path)
            self.load_data()
            self.reconstructed_image=self.imaging_method.image_analysis_method.reconstructed_image
            self.wavelengths=self.imaging_method.image_analysis_method.wavelengths
            
        else:
            self.imaging_method_name=rec.imaging_method_name
            self.reconstructed_image=rec.imaging_method.reconstructed_image
            self.wavelengths=rec.wavelengths
            self.imaging_method=ImagingMethodBridge(self.imaging_method_name)
            self.imaging_method.analysis(self.data_path)
         
    
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
        chemin_script = os.getcwd()
        if self.data_path is None:
            try:
                root = Tk()
                root.withdraw()
                root.attributes('-topmost', 1)
                self.data_path = filedialog.askdirectory(title = "Select the folder containing the acquisitions", initialdir = chemin_script)
                
            except Exception as e:
                print(e)
        os.chdir(self.data_path)
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
        self.imaging_method_name=acq_data["imaging_method"]
        
       
   
    def load_data(self):
        self.imaging_method.image_analysis_method.load_reconstructed_data()
    
    def get_rgb_image(self,datacube,wavelengths):
        rgb_image=self.imaging_method.image_analysis_method.get_rgb_image(datacube,wavelengths)
        return rgb_image

    def plot_rgb_image(self):
        self.imaging_method.image_analysis_method.plot_reconstructed_image(self.reconstructed_image,self.wavelengths) 


