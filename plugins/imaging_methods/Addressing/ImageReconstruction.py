import numpy as np

class Reconstruction:

    def __init__():
         return

    def save(self):              
                
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
        with open(self.json_path, "w") as file:
            json.dump(acq_params, file)
        