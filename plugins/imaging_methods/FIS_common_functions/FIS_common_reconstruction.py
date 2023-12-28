import os
import numpy as np
from tkinter import filedialog
from datetime import date
import time
import spectral.io.envi as envi
import cv2

class FisCommonReconstruction :
    def __init__(self):

        return

    def save_raw_data(self,path=None):
        if path==None: path=f"..{os.sep}Hypercubes"
        root_path=os.getcwd()
        if(os.path.isdir(path)):
            pass
        else:
            os.mkdir(path)
        os.chdir(path)
        
        fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = f"ONE-PIX_raw_acquisition_{fdate}_{actual_time}"
        os.mkdir(folder_name)
        os.chdir(folder_name)
        self.save_path=folder_name

                    
        # Header
        title_param = f"Raw_acquisition_parameters_{fdate}_{actual_time}.txt"
        header = f"ONE-PIX_raw_acquisition_{fdate}_{actual_time}"+"\n"\
            + "--------------------------------------------------------"+"\n"\
            + "\n"\
            + f"Imaging method: {self.imaging_method_name}"+"\n"\
            + "Acquisition duration: %f s" % self.duration+"\n" \
            + f"Spectrometer {self.hardware.name_spectro} : {self.hardware.spectrometer.DeviceName}"+"\n"\
            + f"Camera: {self.hardware.name_camera}" +"\n"\
            + "Number of projected patterns : %d" % self.nb_patterns+"\n" \
            + "Height of pattern window : %d pixels" % self.height+"\n" \
            + "Width of pattern window : %d pixels" % self.width+"\n" \
            + "Number of spectral measures per pattern: %d  " %self.hardware.repetition+"\n" \
            + "Integration time : %d ms" % self.hardware.spectrometer.integration_time_ms+"\n" 
    
    
        text_file = open(title_param, "w+")
        text_file.write(header)
        text_file.close()
        
        
        
        return 


    def save_acquisition_envi(self,datacube,wavelengths,save_envi_name=None,save_path = None):
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
        if save_path is None: save_path=f"..{os.sep}Hypercubes"
        if(os.path.isdir(save_path)):
            pass
        else:
            os.mkdir(save_path)
        os.chdir(save_path)
        
        fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = f"ONE-PIX_reconstructed_data_{fdate}_{actual_time}"
        os.mkdir(folder_name)
        os.chdir(folder_name)
        self.save_path=folder_name
        if save_envi_name is None : folder_name
        # saving the acquired spatial spectra hypercube
        self.py2envi(datacube,wavelengths,save_envi_name,save_path)
        
        
    
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
        if save_path==None:save_path= filedialog.askdirectory(title = "Open the save directory")
        filename=save_envi_name+'.hdr'
        path=os.getcwd()
        os.chdir(save_path)
        envi.save_image(filename,datacube,dtype=np.float32,metadata={'wavelengths':wavelengths,})
        os.chdir(path)