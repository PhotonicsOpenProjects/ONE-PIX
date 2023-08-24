"""
@author:PhotonicsOpenProjects
Modified and traducted by Leo Brechet on Wed Jul 19 18:32:47 2023

"""
import cv2
import io
import os
import sys
import json
import time
import threading
import numpy as np
from datetime import date
import platform
import screeninfo
from tkinter import *
from tkinter.messagebox import askquestion
import PIL

from src.SpectrometerBridge import SpectrometerBridge 
from src.PatternMethods import PatternMethodSelection
from src.DatacubeReconstructions import *
from src.datacube_analyse import *
from src.coregistration_lib import *



def is_raspberrypi():
    """
    is_raspberrypi return a boolean to determine if the current OS is a raspberrry

    """
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False

screenWidth = screeninfo.get_monitors()[0].width
try:
    proj_shape=screeninfo.get_monitors()[1]
except IndexError:
    print('Please use a projector to use ONE-PIX')
    #sys.exit()

class OPConfig:
    """ 
    Class OPConfig is used to set up ONE-PIX acquisitions
    
    :param str spectro_name:
   		Spectrometer concrete bridge implementation:
   		
    :param float integration_time_ms:
   		spectrometer integration time in milliseconds.
           
    """

    def __init__(self,json_path,img=None,nb_patterns=0):
        # Initialize the OPConfig object

        #Get info from acquisition_param_ONE-PIX.json
        f = open(json_path)
        acqui_dict = json.load(f)
        f.close()

        # Pattern method infos
        self.pattern_method = acqui_dict['pattern_method']
        self.spatial_res = acqui_dict['spatial_res']
        self.pattern_lib = PatternMethodSelection(self.pattern_method, self.spatial_res, self.height, self.width)
        self.nb_patterns = self.pattern_lib.nb_patterns
        self.seq_basis = ['FourierSplit','FourierShift']
        self.full_basis = ['Addressing','Custom','Hadamard','BlackAndWhite']
        self.pattern_order = []

        # Spectrometer infos
        self.name_spectro = acqui_dict["name_spectro"]
        self.integration_time_ms =acqui_dict["integration_time_ms"]
        self.spectra = []
        self.wl_lim=acqui_dict["wl_lim"]
        self.spec_lib = SpectrometerBridge(self.name_spectro, self.integration_time_ms,self.wl_lim)
        self.wavelengths = []
        self.spectro_flag=False
        self.rep=acqui_dict["spectro_scans2avg"]

         # Displaying infos
        self.height = acqui_dict['height']
        self.width = acqui_dict["width"]
        self.interp_method=None
        self.periode_pattern=self.rep*self.integration_time_ms
        
        self.duration = 0 #Initialise the duration of a measure


    def get_optimal_integration_time(self):
        """
        This function allows to automatically set the right integration time for 
        ONE-PIX acqusitions depending on the mesurable optical flux. 
    
        Parameters
        ----------
        config : class
            OPConfig class object.
    
        Returns
        -------
        None. Actualisation of the integration_time_ms parameter of config
    
        """
        
        max_counts = 35000
        self.spec_lib.set_integration_time()
        
        flag = True
        self.spectro_flag=True
        count=0
        delta_wl=round(0.05*np.size(self.spec_lib.get_wavelengths()))
        while flag:
            mes = []
            for acq in range(10):
                mes.append(self.spec_lib.get_intensities())
            mes = np.mean(np.array(mes), 0)[delta_wl:-delta_wl]
            delta = max(mes)-max_counts
            print(f"Tint{count}={self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")
    
            if (abs(delta)<2500):
                flag = False
            elif self.spec_lib.integration_time_ms >= 10E3 or self.spec_lib.integration_time_ms==0:
                flag = False
                self.spec_lib.spec_close()
                raise Exception(f"Integration time: {self.spec_lib.integration_time_ms} ms, if you want to continue set the parameter by hand")
                
            elif (count>=10):
                flag=False
                print(f"Measures stopped after {count} iterations. Integration time= {self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")
            else:
                count+=1
                flag = True
                coeff = (max_counts/max(mes))
                self.integration_time_ms = int(self.integration_time_ms*coeff)
                self.spec_lib.integration_time_ms = self.integration_time_ms
                self.spec_lib.set_integration_time()
                
            self.spec_lib.set_integration_time()
            self.spectro_flag=False
        print(f"Integration time (ms): {self.integration_time_ms}")


    def OP_init(self):
        """
        This functions allows to display one Fourier pattern and then adapt and
        set the spectrometer's integration time within the OPConfig class.
    
        Parameters
        ----------
        config : class
            OPConfig class object.
    
        Returns
        -------
        config : class
            actualised OPConfig class object.
    
        """ 
        if self.spec_lib.DeviceName=='':
            self.spec_lib.spec_open()
            self.spec_lib.DeviceName=self.spec_lib.decorator.DeviceName
    
        # create static pattern to be displayed
        proj = Tk()
        proj.geometry("{}x{}+{}+{}".format(self.width, self.height, screenWidth, 0))
        y = list(range(self.height))  # horizontal vector for the pattern creation
        x = list(range(self.width))  # vertical vector for the pattern creation
        Y, X = np.meshgrid(x, y)  # horizontal and vertical array for the pattern creation
        A = 2 * np.pi * X * 10 / self.height
        B = 2 * np.pi * Y * 10 / self.width
        pos_r = np.cos(A + B)  # gray pattern creation
        pos_r[pos_r < 0] = 0

        pil_img = PIL.Image.fromarray(255 * pos_r)

        img = PIL.ImageTk.PhotoImage(master=proj, image=pil_img)
        label_test_proj = Label(proj, image=img)
        label_test_proj.image = img
        label_test_proj.pack()

        # test.r
        proj.update()
        
        print('Finding the optimal integration time (ms):')
        self.get_optimal_integration_time()
        proj.destroy()
        
                    

    def spectrometer_acquisition(self,event):
        """
        spectrometer_acquisition allows to use the spectrometer so that it is synchronised with patterns displays.
    
        Parameters
        ----------
        event : threading.Event 
            event that notifies when pattern is displayed and allow display to continue when cleared.
        config : class
            OPConfig class object.
    
        Returns
        -------
        None. measured spectra are stored in config.
    
        """
        
        cnt=0
        chronograms=np.zeros((self.rep,self.nb_patterns,len(self.wavelengths)))
        
        while cnt <self.nb_patterns:            
            begin=time.time()
                
            if event.is_set():
                for k in range(self.rep):
                    chronograms[k,cnt,:]=self.spec_lib.get_intensities()                
                cnt+=1
                event.clear()
            else:
                time.sleep(1e-6)
            
        self.spectra=np.mean(chronograms,0)       
        #np.save('test',self.spectra)
        self.spec_lib.spec_close()

    
    
    def display_sequence(self,event):
        """
        This function allows to display a sequence of patterns.
       
        Parameters
        ----------
        event : threading Event 
            Ensures the synchronisation between displays and measures
        config : class
            OPConfig class object.
    
        Returns
        -------
        None.
    
        """  
        begin = time.time()
        # Display each pattern from the sequence
        for pattern in self.pattern_lib.decorator.sequence:         
            cv2.imshow('ImageWindow',cv2.resize(pattern,(self.width,self.height),interpolation=self.interp_method))
            cv2.waitKey(self.periode_pattern)
            event.set()
            time.sleep(1e-6)
            while event.is_set():
                time.sleep(1e-6)
            

        cv2.destroyAllWindows()

    def init_display(self):
        """
        This function allows to initialize the display window and the patterns to be displayed before the starts of threads.
    
    
        Parameters
        ----------
        config : class
            OPConfig class object.
    
        Returns
        -------
        config : class
        * actualised OPConfig class object.
        * self.pattern_lib.decorator.sequence : sequence of patterns
        """
        if self.pattern_method in self.seq_basis: # Method used to create, display and measure sequentially patterns within a specific basis
            pattern_reduction=[4,3]
            # horizontal vector for the pattern creation
            x = np.arange(0,self.width//pattern_reduction[0],dtype=np.uint8)
            # vertical vector for the pattern creation
            y = np.arange(0,self.height//pattern_reduction[1],dtype=np.uint8)
            # horizontal and vertical array for the pattern creation
            Y, X = np.meshgrid(x, y)
    
            self.pattern_order, freqs = self.pattern_lib.decorator.sequence_order() # Get spatial frequencies list to create patterns
            self.interp_method=cv2.INTER_NEAREST
            
            for freq in freqs:
                self.pattern_lib.decorator.sequence.extend(self.pattern_lib.decorator.creation_patterns(X, Y, freq))  # Patterns creations 
            
        elif self.pattern_method in self.full_basis:
            self.pattern_order,freq=self.pattern_lib.decorator.creation_patterns()
            self.interp_method=cv2.INTER_AREA
        self.nb_patterns=self.pattern_lib.nb_patterns=len(self.pattern_lib.decorator.sequence)
        print(f"sequence of {self.pattern_lib.nb_patterns} is ready !")
        
        # Spectrometer connection
        if self.spec_lib.DeviceName=='':
            self.spec_lib.spec_open()
        self.spec_lib.set_integration_time()
        self.wavelengths = self.spec_lib.get_wavelengths()
        self.spectra=np.zeros((self.nb_patterns,len(self.wavelengths)),dtype=np.float64)
        # Initialise cv2 display on the second monitor 
        cv2.namedWindow('ImageWindow', cv2.WINDOW_NORMAL)
        cv2.moveWindow('ImageWindow', screenWidth, 0)
        cv2.setWindowProperty("ImageWindow", cv2.WND_PROP_FULLSCREEN, 1)
        cv2.imshow('ImageWindow',cv2.resize(self.pattern_lib.decorator.sequence[0],(self.width,self.height),interpolation=self.interp_method))
        cv2.waitKey(750) # allows the projector to take the time to display the first pattern, particularly if it is white          
       
        
    def thread_acquisition(self, path=None, time_warning=True):
        """
        This funtion allows to run in parallel the projection of a sequence of 
        patterns and spectrometers' measurements in free running mode. 
        The result is measured hyperspectral chronograms need to be processed to 
        extract means spectrums for each patterns.
    
    
        Parameters
        ----------
        config : class
            OPConfig class object.
    
        Returns
        -------
        config : class
        * actualised OPConfig class object.
        * spectra : (array of floats) 2D array of spectra stored in chronological order.
        * wavelengths : (array of floats) 1D wavelengths sampled by the spectrometer.
    
        """
        est_duration=round((self.pattern_lib.nb_patterns*(self.periode_pattern+self.rep*(self.integration_time_ms+2))+2)/(60*1000),2)
        ans='no'
        if time_warning :
            ans=askquestion(message=f"Estimated acquisition duration : {est_duration} min ")
        if np.logical_or(ans=='yes',time_warning==False):
            begin_acq = time.time()
            self.init_display()
            #Threads initialisation
            event=threading.Event()
            patterns_thread = threading.Thread(target=self.display_sequence,args=(event,))
            spectrometer_thread = threading.Thread(target=self.spectrometer_acquisition,args=(event,))
            # Start both display and measure threads
            patterns_thread.start()
            spectrometer_thread.start()
            patterns_thread.join()
            spectrometer_thread.join()

            self.duration = time.time()-begin_acq
            self.save_acquisition_envi(path)
            
        else:
            cv2.destroyAllWindows()
            pass
            
       

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
        
        if self.pattern_method not in ['Custom',"Addressing","BlackAndWhite"]:
            res=OPReconstruction(self.pattern_method,self.spectra,self.pattern_order)
            res.Selection()
            # saving the acquired spatial spectra hypercube
            py2envi(folder_name,res.hyperspectral_image,self.wavelengths,os.getcwd())
        else:
            np.save(folder_name,self.spectra)
            if self.pattern_method=="Addressing":
                title_acq = f"spectra_{fdate}_{actual_time}.npy"
                title_wavelengths = f"wavelengths_{fdate}_{actual_time}.npy"
                title_patterns = f"pattern_order_{fdate}_{actual_time}.npy"
                title_mask= f"mask_{fdate}_{actual_time}.npy"
                np.save(title_mask, self.pattern_lib.decorator.sequence)
                np.save(title_acq, self.spectra)
                np.save(title_wavelengths, self.wavelengths)  # saving wavelength
                np.save(title_patterns, self.pattern_order)  # saving patern order
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
            + "Integration time : %d ms" % self.integration_time_ms+"\n" 
    
    
        text_file = open(title_param, "w+")
        text_file.write(header)
        text_file.close()
        
        
        print('is_raspberrypi() : ',is_raspberrypi())
        if is_raspberrypi():
            root=Tk()
            root.geometry("{}x{}+{}+{}".format(self.width, self.height,screenWidth,0))
            root.wm_attributes('-fullscreen', 'True')
            c=Canvas(root,width=self.width,height=self.height,bg='gray',highlightthickness=0)
            c.pack()
            root.update()
            try:
                from picamera import PiCamera, PiCameraError
                camera = PiCamera()
                camera.resolution = (1024, 768)
                camera.start_preview()
                camera.shutter_speed=7*1176
                camera.vflip=True
                camera.hflip=True
                # Camera warm-up time
                time.sleep(1)
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