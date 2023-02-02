import numpy as np
import cv2
import time
import threading
import os
from datetime import date
import queue
from queue import Queue
import sys
import platform
import datetime

from src.SpectrometerBridge import * 
from src.PatternMethods import *
from src.DatacubeReconstructions import *
from src.datacube_analyse import *
from pathlib import Path
import json
from tkinter import *
from tkinter.messagebox import askquestion


class OPConfig:
    """ 
    Class OPConfig is used to set up ONE-PIX acquisitions
    
    :param str spectro_name:
   		Spectrometer concrete bridge implementation:
   		
    :param float integration_time_ms:
   		spectrometer integration time in milliseconds.
           
    """

    def __init__(self,json_path,img=None,nb_patterns=0):
        f = open(json_path)
        acqui_dict = json.load(f)
        f.close()
        self.height = acqui_dict['height']
        self.width = acqui_dict["width"]
        self.spatial_res = acqui_dict['spatial_res']
        self.pattern_method = acqui_dict['pattern_method']
        self.name_spectro = acqui_dict["name_spectro"]
        self.integration_time_ms =acqui_dict["integration_time_ms"]
        self.mes_ratio=acqui_dict["mes_ratio"]
        
        self.pattern_lib = PatternMethodSelection(self.pattern_method, self.spatial_res, self.height, self.width)
        self.seq_basis = ['FourierSplit','FourierShift']
        self.full_basis = ['Custom','Hadamard']
        self.nb_patterns = self.pattern_lib.nb_patterns

        self.chronograms = []
        self.pattern_order = []
        self.spectra = []

        
        # spectrometer acquistion time in ms
        self.spec_lib = SpectrometerBridge(self.name_spectro, self.integration_time_ms)
        self.wavelengths = []

        self.duration = 0
        self.periode_pattern = self.mes_ratio*self.integration_time_ms
        if self.periode_pattern < 80: self.periode_pattern = 80
        
        self.display_time = []
        self.duree_dark = 2
        self.time_spectro = []
        self.integ_time_flag=True
        self.display=False

def create_banw_sequence(height, width, nb_pattern):
    """
     This function allows to create a sequence containing alternate 
     white and black images.
    
     Parameters
     ----------
     height : int
         heigth of patterns in number of pixel .
     width : int
         with of patterns in number of pixel.
     nb_pattern : int
         total number of images in the B&W sequence.
    
     Returns
     -------
     sequence : array
         sequence of black and white patterns stored in a 3d numpy array.
     pattern_order : list
         list of names of images'names containing white or black and the 
         corresponding chronological position in the sequence.
    
     """

    sequence = np.zeros((height, width, nb_pattern))
    pattern_order = []
    for i in range(nb_pattern):
        pattern_order.append("white_%d" % i)

    for i in range(0, nb_pattern, 2):
        sequence[:, :, i] = 1
        pattern_order[i] = "black_%d" % i

    sequence[0,0,:]=0

    return sequence, pattern_order



def get_optimal_integration_time(config):
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
    
    max_counts = 45000
    config.spec_lib.set_integration_time()
    
    flag = True
    count=0
    while flag:
        #mes=config.spec_lib.get_intensities()[100:-100]
        mes = []
        for acq in range(10):
            mes.append(config.spec_lib.get_intensities())
        mes = np.mean(np.array(mes), 0)[100:-100]
        delta = max(mes)-max_counts
        print(f"Tint{count}={config.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")

        if (abs(delta)<5000):
            flag = False
        elif config.spec_lib.integration_time_ms >= 10E3 or config.spec_lib.integration_time_ms==0:
            flag = False
            config.spec_lib.spec_close()
            raise Exception(f"Integration time: {config.spec_lib.integration_time_ms} ms, if you want to continue set the parameter by hand")
            
        elif (count>=10):
            flag=False
            print(f"Measures stopped after {count} iterations. Integration time= {config.integration_time_ms} ms with intensity peak at {round(max(mes))} counts")
        else:
            count+=1
            flag = True
            coeff = (max_counts/max(mes))
            config.integration_time_ms = int(config.integration_time_ms*coeff)
            config.spec_lib.integration_time_ms = config.integration_time_ms
            config.spec_lib.set_integration_time()
            
        config.spec_lib.set_integration_time()
        
    print(f"Integration time (ms): {config.integration_time_ms}")


def OP_init(config):
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
           
        
    os_name = platform.system()
    if config.spec_lib.DeviceName=='':
        config.spec_lib.spec_open()
        config.spec_lib.DeviceName=config.spec_lib.decorator.DeviceName

    if os_name == 'Windows':
        x=list(range(config.height)) # horizontal vector for the pattern creation 
        y=list(range(config.width))# vertical vector for the pattern creation
        Y,X = np.meshgrid(x,y)# horizontal and vertical array for the pattern creation
        A=2*np.pi*X*1/config.height
        B=2*np.pi*Y*5/config.width
        pos_r=np.cos(A+B) #gray pattern creation
        
        cv2.namedWindow('Init', cv2.WINDOW_NORMAL)
        cv2.moveWindow('Init', 1920, 0)
        cv2.setWindowProperty("Init", cv2.WND_PROP_FULLSCREEN, 1)
        cv2.imshow('Init', pos_r)
        cv2.waitKey(300)
    print('Finding the optimal integration time (ms):')
    get_optimal_integration_time(config)
    cv2.destroyAllWindows()
    
    config.periode_pattern = config.mes_ratio*config.integration_time_ms

    if config.periode_pattern < 80:
        config.periode_pattern = 80
    #config.spec_lib.set_integration_time()
    return config


def spectrometer_acquisition(q, config):
    """
    This function allows to use the spectrometer in free runing mode to record 
    a chronogram of acquisitions.

    Parameters
    ----------
    q : Queue 
        queue to check when patterns display is over.
    config : class
        OPConfig class object.

    Returns
    -------
    None. chronograms are stored in config.

    """
    
    begin = time.time()
    # Spectrometer connection
    if config.spec_lib.DeviceName=='':
        config.spec_lib.spec_open()
    config.spec_lib.set_integration_time()
    config.wavelengths = config.spec_lib.get_wavelengths()
    flag=True
    while True:
        flag=config.integ_time_flag
        if flag:
            config.chronograms.append(np.asarray(config.spec_lib.get_intensities(), dtype=np.float32))
            config.time_spectro.append((time.time()-begin)*1e3)
        else:
            
            config.chronograms.append(2*np.asarray(config.spec_lib.get_intensities(), dtype=np.float32))
            config.time_spectro.append((time.time()-begin)*1e3)

        try:
            q.get_nowait()
            break

        except queue.Empty:
            pass

    config.spec_lib.spec_close()
    #config.chronograms = np.array(config.chronograms)


"""

Inputs :
    q : queue to indicate when the videoprojector display ended and stop measures
    sequence : sequence of pattern to be display with the video projector 
    periode_pattern : projection time for one pattern
    duree_dark : porjection time of the black pattern between patterns to display

Outputs :
    This function don't have local variable outputs to be compatible with threading.
    Outputs variables are stored in files :
    display_time.npy : containing the time of the beginning and the end of projection for each pattern  

"""

def affichage_sequence(q, config):
    """
    This function allows to display a sequence of patterns.
   
    Parameters
    ----------
    q : Queue 
        queue to check when patterns display is over.
    config : class
        OPConfig class object.

    Returns
    -------
    None.

    """
    
    os_name = platform.system()

    begin = time.time()

    black_patterns = np.zeros((config.height, config.width,10))
    temps = []
    pattern_tampon = 12
    #sequence_tampon, un = create_banw_sequence(config.height, config.width, pattern_tampon)

    cv2.namedWindow('ImageWindow', cv2.WND_PROP_FULLSCREEN)
    if os_name=='Windows':
        cv2.moveWindow('ImageWindow', 1920, 0)
    else:
        cv2.moveWindow('ImageWindow', 1024, 0)
       
    cv2.setWindowProperty("ImageWindow", cv2.WND_PROP_FULLSCREEN, 1)
    for i in range(0, np.size(black_patterns, 2)):

        cv2.imshow('ImageWindow', black_patterns[:, :, i])
        cv2.waitKey(round(config.periode_pattern))
        

    if config.pattern_method in config.seq_basis:
        # horizontal vector for the pattern creation
        x = list(range(config.width))
        # vertical vector for the pattern creation
        y = list(range(config.height))
        # horizontal and vertical array for the pattern creation
        Y, X = np.meshgrid(x, y)

        config.pattern_order, freqs = config.pattern_lib.decorator.sequence_order()

        for freq in freqs:
            patterns = config.pattern_lib.decorator.creation_patterns(X, Y, freq)  # patterns creations 
                
            for pattern in patterns:
                if freq==(0,0):
                    config.integ_time_flag=False
                    config.spec_lib.integration_time_ms=config.spec_lib.integration_time_ms/2
                    config.spec_lib.set_integration_time()
                
                temps.append(time.time())
                cv2.imshow('ImageWindow', pattern)
                cv2.waitKey(round(config.periode_pattern))
                temps.append(time.time())
                
                if freq==(0,0):
                    config.integ_time_flag=True
                    config.spec_lib.integration_time_ms=config.spec_lib.integration_time_ms*2
                    config.spec_lib.set_integration_time()
                
                

    elif config.pattern_method in config.full_basis:
        for pattern in config.pattern_lib.decorator.sequence:
            temps.append(time.time())
            cv2.imshow('ImageWindow', cv2.resize(pattern,(800,600),interpolation=cv2.INTER_AREA))
            cv2.waitKey(round(config.periode_pattern))
            temps.append(time.time())

    time.sleep(0.1)
    q.put(True)

    cv2.destroyAllWindows()
    config.display_time = (np.asarray(temps)-begin)*1e3


def thread_acquisition(config):
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
    * display_time : (array of floats) 1D array of time values of the beginning and the end of projection for each pattern. 
    * time_spectro : (array of floats) 1D array of time values for each measured spectrum.
    * chronograms : (array of floats) 3D array of spectra stored in chronological order.
    * wavelengths : (array of floats) 1D wavelengths sampled by the spectrometer.

    """
    
    begin_acq = time.time()
    if config.pattern_method in config.full_basis:
        config.pattern_order,freq=config.pattern_lib.decorator.creation_patterns()
        config.pattern_lib.nb_patterns=config.pattern_lib.decorator.nb_patterns
    est_duration=round(1.5*config.pattern_lib.nb_patterns*config.periode_pattern/(60*1000),2)
    ans=askquestion(message=f"Estimated acquisition duration : {est_duration} min ")
    if ans=='yes':
        est_end=(datetime.datetime.now()+datetime.timedelta(minutes=round(est_duration))).strftime('%H:%M:%S')
        print("Estimated end of the acquisition: "+est_end)
        q = Queue()
        first_thread = threading.Thread(
            target=affichage_sequence, args=(q, config))
        second_thread = threading.Thread(
            target=spectrometer_acquisition, args=(q, config))
        first_thread.start()
        second_thread.start()

        first_thread.join()
        second_thread.join()

        config.duration = time.time()-begin_acq

        save_acquisition_envi(config)
    else:
        pass
   
    return config

def save_acquisition_envi(config):
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
    
    #extract spectra from chronograms
    config.display_time = time_aff_corr(
        config.chronograms, config.time_spectro, config.display_time)
    config.spectra = calculate_pattern_spectrum(
        config.display_time, 0, config.time_spectro, config.chronograms, 0)
    
    res=OPReconstruction(config.pattern_method,config.spectra,config.pattern_order)
    res.Selection()
    
    root_path=os.getcwd()
    path=os.path.join(root_path,'Hypercubes')
    if(os.path.isdir(path)):
        pass
    else:
        os.mkdir('Hypercubes')
    os.chdir(path)
    
    fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
    actual_time = time.strftime("%H-%M-%S")  # get the current time
    
    title_acq = f"spectra_{fdate}_{actual_time}.npy"
    

    folder_name = f"ONE-PIX_acquisition_{fdate}_{actual_time}"
    os.mkdir(folder_name)
    os.chdir(folder_name)
    # saving the acquired spatial spectra hypercube
    py2envi(folder_name,res.hyperspectral_image,config.wavelengths,os.getcwd())

    # Header
    title_param = f"Acquisition_parameters_{fdate}_{actual_time}.txt"

    header = f"ONE-PIX acquisition_{fdate}_{actual_time}"+"\n"\
        + "--------------------------------------------------------"+"\n"\
        + "\n"\
        + f"Acquisition method : {config.pattern_method}"+"\n"\
        + "Acquisition time : %f s" % config.duration+"\n" \
        + f"Spectrometer {config.name_spectro} : {config.spec_lib.DeviceName}"+"\n"\
        + "Number of projected patterns : %d" % config.nb_patterns+"\n" \
        + "Height of pattern window : %d pixels" % config.height+"\n" \
        + "Width of pattern window : %d pixels" % config.width+"\n" \
        + "Dark pattern duration : %d ms" % config.duree_dark+"\n" \
        + "Integration time : %d ms" % config.integration_time_ms+"\n" 


    text_file = open(title_param, "w+")
    text_file.write(header)
    text_file.close()
    
    
    os_name=platform.system()
    if os_name=='Linux':
        try:
            root=Tk()
            root.geometry("{}x{}+{}+{}".format(800, 600,1024,0))
            root.wm_attributes('-fullscreen', 'True')
            c=Canvas(root,width=800,height=600,bg='black',highlightthickness=0)
            c.pack()
            root.update()

            from picamera import PiCamera, PiCameraError
            camera = PiCamera()
            camera.resolution = (1024, 768)
            camera.start_preview()
            camera.shutter_speed=7*1176
            camera.vflip=True
            camera.hflip=True
            # Camera warm-up time
            time.sleep(2)
            camera.capture(f"RGBCam_{fdate}_{actual_time}.jpg")
            camera.close()
            root.destroy()
        except PiCameraError:
            print("Warning; check a RPi camera is connected. No picture were stored !")
            root.destroy()
    os.chdir(root_path)
    del config.chronograms,config.time_spectro, config.display_time # saves RAM for large acquisitions

def save_acquisition(config):
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
    
    #extract spectra from chronograms
    config.display_time = time_aff_corr(
        config.chronograms, config.time_spectro, config.display_time)
    config.spectra = calculate_pattern_spectrum(
        config.display_time, 0, config.time_spectro, config.chronograms, 0)
    
    
    
    root_path=os.getcwd()
    path=os.path.join(root_path,'Hypercubes')
    if(os.path.isdir(path)):
        pass
    else:
        os.mkdir('Hypercubes')
    os.chdir(path)
    
    fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
    actual_time = time.strftime("%H-%M-%S")  # get the current time
    
    title_acq = f"spectra_{fdate}_{actual_time}.npy"
    title_wavelengths = f"wavelengths_{fdate}_{actual_time}.npy"
    title_patterns = f"pattern_order_{fdate}_{actual_time}.npy"

    folder_name = f"ONE-PIX_acquisition_{fdate}_{actual_time}"
    os.mkdir(folder_name)
    os.chdir(folder_name)
    # saving the acquired spatial spectra hypercube
    np.save(title_acq, config.spectra)
    np.save(title_wavelengths, config.wavelengths)  # saving wavelength
    np.save(title_patterns, config.pattern_order)  # saving wavelength

    # Header
    title_param = f"Acquisition_parameters_{fdate}_{actual_time}.txt"

    header = f"ONE-PIX acquisition_{fdate}_{actual_time}"+"\n"\
        + "--------------------------------------------------------"+"\n"\
        + "\n"\
        + f"Acquisition method : {config.pattern_method}"+"\n"\
        + "Acquisition duration : %f s" % config.duration+"\n" \
        + f"Spectrometer {config.name_spectro} : {config.spec_lib.DeviceName}"+"\n"\
        + "Pattern duration : %d ms" % config.periode_pattern+"\n" \
        + "Integration time : %d ms" % config.integration_time_ms+"\n"\
        + "Number of projected patterns : %d" % config.nb_patterns+"\n" \
        + "Height of pattern window : %d pixels" % config.height+"\n" \
        + "Width of pattern window : %d pixels" % config.width+"\n" 


    text_file = open(title_param, "w+")
    text_file.write(header)
    text_file.close()
    
    
    os_name=platform.system()
    if os_name=='Linux':
        try:
            root=Tk()
            root.geometry("{}x{}+{}+{}".format(800, 600,1024,0))
            root.wm_attributes('-fullscreen', 'True')
            c=Canvas(root,width=800,height=600,bg='black',highlightthickness=0)
            c.pack()
            root.update()

            from picamera import PiCamera
            camera = PiCamera()
            camera.resolution = (1024, 768)
            camera.start_preview()
            camera.shutter_speed=7*1176
            camera.vflip=True
            camera.hflip=True
            # Camera warm-up time
            time.sleep(2)
            camera.capture(f"RGBCam_{fdate}_{actual_time}.jpg")
            camera.close()
            time.sleep(1)
            root.destroy()
        except PiCamera.PiCameraError:
            print("Warning; check a RPi camera is connected. No picture were stored !")
            
    os.chdir(root_path)
    del config.chronograms # saves RAM for large acquisitions

    
