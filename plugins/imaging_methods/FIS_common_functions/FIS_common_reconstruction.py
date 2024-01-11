import os
import numpy as np
from tkinter import filedialog
from datetime import date
import time
import spectral.io.envi as envi
import cv2

class FisCommonReconstruction :
    def __init__(self,acquisition_dict=None):
        self.acquisition_dict=acquisition_dict
        return



    def save_acquisition_envi(self,datacube,wavelengths,header,save_envi_name=None,save_path = None):
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
        root_path=os.getcwd()
        if save_path is None: save_path=f"..{os.sep}Hypercubes"
        if(os.path.isdir(save_path)):
            pass
        else:
            os.mkdir(save_path)
        os.chdir(save_path)
        
        self.fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        self.actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = f"ONE-PIX_reconstructed_data_{self.fdate}_{self.actual_time}"
        os.mkdir(folder_name)
        os.chdir(folder_name)
        self.save_path=folder_name
        if save_envi_name is None : save_envi_name=folder_name
        # saving the acquired spatial spectra hypercube
        self.py2envi(datacube,wavelengths,save_envi_name,save_path)
        with open(folder_name+'.txt', "w+") as header_file:
            header_file.write(header)
        os.chdir(root_path)

    def py2envi(self,datacube,wavelengths,save_envi_name,save_path=None):
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
        filename=save_envi_name+'.hdr'
        path=os.getcwd()
        if save_path==None:
            save_path= filedialog.askdirectory(title = "Open the save directory")
            os.chdir(save_path)
            envi.save_image(filename,datacube,dtype=np.float32,metadata={'wavelength': wavelengths})
            os.chdir(path)
        else:
            envi.save_image(filename,datacube,dtype=np.float32,metadata={'wavelength': wavelengths})
        
        
        

    


    def py2ms(self,datacube,wavelengths,save_gerbil_name):
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
        
        save_path= filedialog.askdirectory(title = "Open the save directory")        
        maxval = datacube.max()
        minval = datacube.min()
        Range = maxval - minval
        datacube = (datacube + minval) * (255/Range)
        
        fid= open(save_path+'\\'+save_gerbil_name+'.txt','w')
        os.mkdir(save_path+'\\'+save_gerbil_name)
        nz = np.shape(datacube)
        
        fid.write('{0} {1} \n'.format(nz[2],save_gerbil_name+'\\'))
        
        for i in range(0,nz[2]):
            filename = '{0}_{1}.png'.format(save_gerbil_name,i)
            cv2.imwrite(save_path+'\\'+save_gerbil_name+'\\'+filename,datacube[:,:,i])
            fid.write( '{0} {1}\n'.format( filename, wavelengths[i]))

        fid.close()
        
    