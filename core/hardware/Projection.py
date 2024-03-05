import cv2
import screeninfo 
import numpy as np
import time
from tkinter import *
import PIL.Image, PIL.ImageTk

screenWidth = screeninfo.get_monitors()[0].width
try:
    proj_shape=screeninfo.get_monitors()[1]
except IndexError:
    print('Please use a projector to use ONE-PIX')
    #sys.exit()


class Projection:
    """
     Allows to build a generic bridge based on a concrete one. Concrete 
     bridge provides correct implementation regarding spectrometer model
     use. The generic bridge is an abstract layer that wrap concrete implementation.
    
     :param str spectro_name:
    		Spectrometer concrete bridge implementation:
    		
     :param float integration_time_ms:
    		spectrometer integration time in milliseconds.
    """
    
    def __init__(self,height,width,periode_pattern,proj_position):
        self.height=height
        self.width=width
        self.periode_pattern=periode_pattern
        self.proj_position=proj_position

        try:
            self.proj_shape=np.array([proj_shape.height,proj_shape.width])
        except Exception as e:
            pass

    def create_fullscreen_window(self):
        # Initialise cv2 display on the second monitor 
        cv2.namedWindow('ImageWindow', cv2.WINDOW_NORMAL)
        cv2.moveWindow('ImageWindow', screenWidth, 0)
        cv2.setWindowProperty("ImageWindow", cv2.WND_PROP_FULLSCREEN, 1)
    
    def create_integrated_frame(self):
        # Backgroung black image 
        cv2.namedWindow('background', cv2.WINDOW_NORMAL)
        cv2.moveWindow('background', screenWidth, 0)
        cv2.setWindowProperty("background", cv2.WND_PROP_FULLSCREEN, 1)
        cv2.imshow("background",np.zeros(self.proj_shape))
        # Image disposed at proj_position from hardware json
        cv2.namedWindow('ImageWindow', flags=cv2.WINDOW_GUI_EXPANDED)
        cv2.setWindowProperty("ImageWindow", cv2.WND_PROP_FULLSCREEN, 1)
        cv2.moveWindow('ImageWindow', screenWidth+self.proj_position[0], self.proj_position[1])
        cv2.resizeWindow('ImageWindow', self.width, self.height)
        cv2.setWindowProperty("ImageWindow",cv2.WND_PROP_TOPMOST , 1)


    def get_integration_time_auto(self,acq_config):
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
        
        y = list(range(self.height))  # horizontal vector for the pattern creation
        x = list(range(self.width))  # vertical vector for the pattern creation
        Y, X = np.meshgrid(x, y)  # horizontal and vertical array for the pattern creation
        A = 2 * np.pi * X * 10 / self.height
        B = 2 * np.pi * Y * 10 / self.width
        test_pattern = np.cos(A + B)  # gray pattern creation
        test_pattern[test_pattern < 0] = 0
        
        
        self.create_fullscreen_window()
        cv2.imshow('ImageWindow',cv2.resize(test_pattern,(self.width,self.height),interpolation=cv2.INTER_LINEAR_EXACT))
        cv2.waitKey(1)
        time.sleep(0.5)
        print('Finding the optimal integration time (ms):')
        acq_config.hardware.spectrometer.get_optimal_integration_time()
        acq_config.periode_pattern=int(acq_config.hardware.repetition*acq_config.hardware.spectrometer.integration_time_ms)
        if acq_config.periode_pattern<60 :acq_config.periode_pattern=60
        cv2.destroyAllWindows()

    def init_projection(self,patterns,patterns_order,interp_method):
        # Initialise cv2 display on the second monitor 
        self.create_fullscreen_window() if np.all(self.proj_position=='auto') else self.create_integrated_frame()
        cv2.imshow('ImageWindow',cv2.resize(patterns[0],(self.width,self.height),interpolation=interp_method))
        cv2.waitKey(750) # allows the projector to take the time to display the first pattern, particularly if it is white     

    def thread_projection(self,event,patterns,patterns_order,interp_method):
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
        self.init_projection(patterns,patterns_order,interp_method)         
        """
        try:
            white_idx=self.pattern_lib.decorator.white_pattern_idx
        except:           
            white_idx=-100
        delta_idx=4 if self.pattern_method=='FourierSplit' else 2
        """
        # Display each pattern from the sequence
        for count,pattern in enumerate(patterns):
            """""
            if  count in np.arange(white_idx,white_idx+delta_idx):
                self.spectro_flag=True
        
            """
            cv2.imshow('ImageWindow',cv2.resize(pattern,(self.width,self.height),interpolation=interp_method))
            cv2.waitKey(int(self.periode_pattern))
            event.set()
            time.sleep(1e-6)
            while event.is_set():
                time.sleep(1e-6)
            

        cv2.destroyAllWindows()
