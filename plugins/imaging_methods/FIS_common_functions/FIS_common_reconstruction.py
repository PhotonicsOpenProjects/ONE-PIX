import os
import numpy as np


class FisCommonReconstruction :
    def __init__(self) 

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
        
        np.save()
        
        return 


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