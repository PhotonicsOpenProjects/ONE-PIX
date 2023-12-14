import numpy as np 
import matplotlib.pyplot as plt 
import os
import glob
import tkinter as Tk
from tkinter import filedialog
from tkinter import *
import importlib
from sklearn import mixture
import spectral.io.envi as envi
import time
#%% Raw data pre-treatment


def get_header_data(path):
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
    
    header=[]
    with open(path, 'r') as file:
       for line in file.readlines():
           header.append(line.split(':'))
    acq_data=dict()
    acq_data['Acquisition_name']=header[0][0][8:]
    for x in header:
        if x[0].strip()=='Acquisition method':
            acq_data['pattern_method']=x[1].strip()
        
        if x[0].strip()=='Integration time':
            acq_data['integration_time_ms']=float(x[1].strip()[:-2])
    
    return acq_data


def load_spectra():
    """
    This function allows to load saved spectra with timers of the displays and spectrometers.
    at runtime, a window appears to select the folder path in which the data are located. 

    Returns
    -------
    acq_data : dict
        Dictionary containing data extracted from files saved after acquisition to reconstruct data cubes.

    """
   
    
    chemin_script = os.getcwd()
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', 1)
    chemin_mesure = filedialog.askdirectory(title = "Select the folder containing the acquisitions", initialdir = chemin_script)
    os.chdir(chemin_mesure)
    
    header_name=glob.glob('*.txt')[0]
    acq_data=get_header_data(header_name)
    
    list_nom_mesure = sorted(glob.glob('*.npy'),key=os.path.getmtime)
    
    indice=[x for x, s in enumerate(list_nom_mesure) if "spectra" in s]
    acq_data['spectra']=np.load(list_nom_mesure[indice[0]])
       
    indice=[x for x, s in enumerate(list_nom_mesure) if "wavelengths" in s]
    acq_data['wavelengths']=np.load(list_nom_mesure[indice[0]])
    
    indice=[x for x, s in enumerate(list_nom_mesure) if "pattern_order" in s]
    acq_data['pattern_order']=np.load(list_nom_mesure[indice[0]])
    
    os.chdir(chemin_script)
    
    return acq_data

def load_hypercube(opt=None):
    """
    This function allows to load saved spectra with timers of the displays and spectrometers.
    at runtime, a window appears to select the folder path in which the data are located. 

    Returns
    -------
    acq_data : dict
        Dictionary containing data extracted from files saved after acquisition to reconstruct data cubes.

    """
   
    # root = Tk()
    # root.withdraw()
    # root.attributes('-topmost', 1)
    res={"hyperspectral_image":[],"wavelengths":[]}
    
    if opt==None:
        if os.path.isdir('./Hypercubes'):
            data_folder='./Hypercubes'
        elif '../Hypercubes':
            data_folder='../Hypercubes'
        else:
            data_folder=os.getcwd()    

        meas_path = filedialog.askdirectory(title = "Select the folder containing the acquisitions",initialdir=data_folder)
    elif opt=='last':
        root_path=os.getcwd()
        path=os.path.join(root_path,'Hypercubes')
        meas_path=max(glob.glob(os.path.join(path, '*/')), key=os.path.getmtime)
       
    else:
        meas_path=opt
        
    hyp_filename=glob.glob(f'{meas_path}/*.hdr')[0]
    try:
        info_filename=glob.glob(f'{meas_path}/*.txt')[0]
        res['pattern_method']=get_header_data(info_filename)['pattern_method']
    except:
        pass
    res['infos']='ONE_PIX_analysis'+meas_path.split('/')[-1][19:]
    data=envi.open(hyp_filename)
    res["hyperspectral_image"]=data.load()
    res["wavelengths"]=np.array(data.bands.centers)
       
    
    return res



    
def snr_filt(self,spectre_desplit,noise_level=500):
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
    M=np.max(abs(spectre_desplit),axis=1)
    idx_noise=np.squeeze(np.array(np.where(M<noise_level)))
    spectre_desplit[idx_noise,:]=0
    return spectre_desplit



def save_acquisition_envi(self, path = "../Hypercubes"):
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
        if path==None: path="../Hypercubes"
        root_path=os.getcwd()
        #path=os.path.join(root_path,'Hypercubes')
        if(os.path.isdir(path)):
            pass
        else:
            os.mkdir(path)
        os.chdir(path)
        
        fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = f"ONE-PIX_acquisition_{fdate}_{actual_time}"
        os.mkdir(folder_name)
        os.chdir(folder_name)
        self.save_path=folder_name
        if self.pattern_method not in ['Custom',"Addressing","BlackAndWhite"]:
            self.res=OPReconstruction(self.pattern_method,self.spectra,self.pattern_order)
            self.res.Selection()
            # saving the acquired spatial spectra hypercube
            if self.normalisation_path !='':
                # Load raw data
                acq_data=load_hypercube(self.normalisation_path)
                ref_datacube=acq_data['hyperspectral_image']
                if(np.shape(ref_datacube)!=np.shape(self.res.hyperspectral_image)):
                    ref=np.zeros_like(self.res.hyperspectral_image)
                    for wl in range(np.size(ref,2)):
                        ref[:,:,wl]=cv2.resize(ref_datacube[:,:,wl],(np.shape(ref)[:2]))
                else: ref=ref_datacube
                
                self.normalised_datacube=self.res.hyperspectral_image/ref
                
                py2envi(folder_name+'_normalised',self.normalised_datacube,self.wavelengths,os.getcwd())
            py2envi(folder_name,self.res.hyperspectral_image,self.wavelengths,os.getcwd())
            
        else:              
            if self.pattern_method=="Addressing":
                # dark pattern correction
                self.spectra-=self.spectra[-1,:]
                self.spectra=self.spectra[:-1,:]
                
                if self.normalisation_path !='':
                    try:
                        # Load raw data
                        acq_data=load_hypercube(self.normalisation_path)
                        ref_datacube=acq_data['hyperspectral_image']
                        masks=np.asarray(self.pattern_lib.decorator.sequence)[:-1,:,:]
                        nb_masks=np.size(masks,0)
                        print(f"{nb_masks=}")
                        new_masks=np.zeros((nb_masks,np.size(ref_datacube,0),np.size(ref_datacube,1)))
                        for idx in range(nb_masks):
                            new_masks[idx,:,:]=cv2.resize(masks[idx,:,:],np.shape(new_masks[idx,:,:]),interpolation=cv2.INTER_AREA)


                        ref_spec=np.zeros((nb_masks,np.size(ref_datacube,2)))
                        for idx in range(nb_masks):
                            mask=np.where(new_masks[idx,:,:],new_masks[idx,:,:],np.nan)/255
                            for wl in range(np.size(ref_datacube,2)):
                                ref_spec[idx,wl]=np.nanmean(ref_datacube[:,:,wl].squeeze()*mask,axis=(0,1))

                        ref_spec-=np.repeat(np.nanmean(ref_spec[:,:10],axis=1)[:,np.newaxis],np.size(ref_datacube,2),axis=1)
                        
                        self.normalised_datacube=self.spectra/ref_spec
                        title_acq = f"spectra_normalised_{fdate}_{actual_time}.npy"
                        np.save(title_acq,self.normalised_datacube)
                    except Exception as e:
                        print(e)


                title_acq = f"spectra_{fdate}_{actual_time}.npy"
                title_wavelengths = f"wavelengths_{fdate}_{actual_time}.npy"
                #title_patterns = f"pattern_order_{fdate}_{actual_time}.npy"
                title_mask= f"mask_{fdate}_{actual_time}.npy"
                np.save(title_mask, self.pattern_lib.decorator.sequence)
                np.save(title_acq, self.spectra)
                np.save(title_wavelengths, self.wavelengths)  # saving wavelength
                #np.save(title_patterns, self.pattern_order)  # saving patern order
        # Header
        title_param = f"Acquisition_parameters_{fdate}_{actual_time}.txt"
        header = f"ONE-PIX acquisition_{fdate}_{actual_time}"+"\n"\
            + "--------------------------------------------------------"+"\n"\
            + "\n"\
            + f"Acquisition method : {self.pattern_method}"+"\n"\
            + "Acquisition duration : %f s" % self.duration+"\n" \
            + f"Spectrometer {self.name_spectro} : {self.spec_lib.DeviceName}"+"\n"\
            + "Number of projected patterns : %d" % self.nb_patterns+"\n" \
            + "Height of pattern window : %d pixels" % self.height+"\n" \
            + "Width of pattern window : %d pixels" % self.width+"\n" \
            + "Number of spectral measures per pattern: %d  " %self.rep+"\n" \
            + "Integration time : %d ms" % self.integration_time_ms+"\n" 
    
    
        text_file = open(title_param, "w+")
        text_file.write(header)
        text_file.close()
        
        print('is_raspberrypi() : ',is_raspberrypi())
        if is_raspberrypi():
            root=Tk()
            root.geometry("{}x{}+{}+{}".format(self.width, self.height,screenWidth,0))
            root.wm_attributes('-fullscreen', 'True')
            c=Canvas(root,width=self.width,height=self.height,bg='black',highlightthickness=0)
            c.pack()
            root.update()
            try:
                from picamera import PiCamera, PiCameraError
                camera = PiCamera(resolution = (1024, 768))
                camera.iso=300
                time.sleep(2)
                camera.shutter_speed = camera.exposure_speed
                camera.exposure_mode = 'off'
                g = camera.awb_gains
                camera.awb_mode = 'off'
                camera.awb_gains = g
                camera.vflip=True
                camera.hflip=True

                camera.capture(f"RGBCam_{fdate}_{actual_time}.jpg")
                camera.close()
                
                if(self.pattern_method=='Addressing'):
                    rgb_name=f"RGBCam_{fdate}_{actual_time}.jpg"
                    RGB_img = cv2.imread(rgb_name)
                    RGB_img= np.asarray(RGB_img)
                    os.chdir(root_path)
                    print('acq_conf_cor_path', os.path.abspath(os.curdir))
                    RGB_img=apply_corregistration(RGB_img,'../acquisition_param_ONEPIX.json')
                    os.chdir(path)
                    os.chdir(folder_name)
                    print('corPath : ',os.getcwd())
                    cv2.imwrite(f"RGB_cor_{fdate}_{actual_time}.jpg",RGB_img)
            except PiCameraError:
                print("Warning; check a RPi camera is connected. No picture were stored !")
            root.destroy()
        os.chdir(root_path)
        f = open(self.json_path)
        acq_params = json.load(f)
        f.close()
        acq_params["normalisation_path"] = ""
        file = open(self.json_path, "w")
        json.dump(acq_params, file)
        file.close()


#%% method Selection

class OPReconstruction:
    """ Class OPReconstruction to reconstruct datacubes according to a ONE-PIX method"""
    def __init__(self,imag_method,spectra,pattern_order):
        self.imag_method=imag_method
        self.spectra=spectra 
        
        self.pattern_order=pattern_order
        self.hyperspectral_image=[]
        self.whole_spectrum=[]
        
        try:
            module='src.reconstructions_methods'
            className=imag_method+'Reconstruction'
            module=importlib.import_module('src.reconstructions_methods.'+className)
            classObj = getattr(module, className)
            self.decorator = classObj(spectra,pattern_order)
        except:
            raise Exception("Concrete bridge \"" + imag_method + "\" implementation has not been found.")
#         if not isinstance(self.decorator, AbstractBridge):
#             raise Exception("Concrete bridge \"" + spectro_name + "\" must implement class bridges.AbstractBridge.")
         
    def nan_corr(self):
        """
        nan_corr allows to filter nan from acquired spectra

        Returns
        -------
        None.

        """
        try:
            idx_nan=np.argwhere(np.isnan(self.spectra))[0,:-1]
            self.spectra[idx_nan,:]=self.spectra[idx_nan-1,:]
        except IndexError:
            pass
        
    def Selection(self):
        """
        This function allows to reconstruct spatial spectra and images data cubes.
        These data are stored in the OPReconstruction class object.

        Returns
        -------
        None.

        """
        self.nan_corr()
        self.whole_spectrum,self.hyperspectral_image=self.decorator.datacube_reconstruction()
        
       
    def image_reconstruction(self):
        """
        image_reconstruction allows to reconstruct an image data cube from an actualised 
        spatial spectra data cube. Both are stored in the HSPIReconstruction class object.

        Returns
        -------
        None.

        """
        if self.imag_method in ['FourierSplit','FourierShift']:
            self.hyperspectral_image=np.abs(np.fft.ifftn(self.whole_spectrum,axes=(0,1)))
        
        elif self.imag_method=='Hadamard':
            self.hyperspectral_image=self.Hadamard_reconstruction()
