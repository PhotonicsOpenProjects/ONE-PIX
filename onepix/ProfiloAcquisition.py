from core.hardware.HardwareConfig import *
import cv2
import os
import time
import threading
import numpy as np
from datetime import date
import time

class Profilo_Acquisition :

    def __init__(self,patterns,pattern_order):
        self.hard=Hardware()
        self.patterns=patterns
        self.repetition=4
        self.is_init = False
        self.pattern_order=pattern_order
        self.interp_method=cv2.INTER_AREA
        pass

    def init_measure(self):

            if not (self.is_init):
                try:
                    self.nb_patterns = np.shape(self.patterns)[0]
                    print("nb de patterns",self.nb_patterns)
                    self.is_init = True
                    self.hard.camera.camera_open()
                    self.hard.camera.camera.get_image_var()
                    img_test=self.hard.camera.camera.image
                    print("image_ests",np.shape(img_test))
                    self.img_dim=np.shape(img_test)
                    
                except Exception as e:
                    print(e)
                    self.is_init = False
            else:
                pass




    def camera_thread(self, event):
          
        try:
            cnt = 0
            self.camera_measure = np.zeros((self.nb_patterns,self.img_dim[0],self.img_dim[1]))
            while cnt < self.nb_patterns:
                
                # Measure intensities for the current pattern
                mes_stack = []
                for _ in range(self.repetition):
                    self.hard.camera.camera.get_image_var()
                    mes=self.hard.camera.camera.image
                    print("image size in trhead",np.shape(mes))
                    if mes is None:
                        raise RuntimeError("Failed to get image from camera.")
                    mes_stack.append(mes)
                # Average the measurements and store the result in spectra
                mes_stack=np.asarray(mes_stack)
                self.camera_measure[cnt, :,:] = np.mean( mes_stack, axis=0) 
                    
                cnt += 1
                event.clear()  # Clear event to wait for the next pattern
            
                
        except Exception as e:
            # Log error for debugging
            print(f"An error occurred during spectrometer acquisition: {e}")

        finally:
            # Ensure the camera is closed properly
            self.hard.camera.close_camera()

    
    def profilo_thread_acquisition(self, path=None ):

        self.init_measure()

        # Begin acquisition process
        begin_acq = time.time()
        
        # Threads initialization
        event = threading.Event()
        
        # Define threads for pattern projection and spectrometer measurement
        patterns_thread = threading.Thread(
            target=self.hard.projection.thread_projection,
            args=(
                event,
                self.patterns,
                self.pattern_order,
                self.interp_method,
            )
        )
        
        camera_thread = threading.Thread(
            target=self.camera_thread,
            args=(event,)
        )

        try:
            # Start threads
            patterns_thread.start()
            camera_thread.start()

            # Wait for threads to complete
            patterns_thread.join()
            camera_thread.join()
            print("threading mes finish")
            # Retrieve data after the threads finish
            self.duration = time.time() - begin_acq
            


        except Exception as e:
            # Handle any potential errors during the acquisition process
            print(f"An error occurred during profilo acquisition: {e}")
            cv2.destroyAllWindows()

        finally:
            self.is_init = False

    
    def save_raw_data(self,save_path=None):
        if save_path==None:
            save_path= os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "Hypercubes")
        
            if os.path.isdir(save_path):
                pass
            else:
                os.mkdir(save_path)
                
        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        profilo_mes_title=folder_name = f"ONE-PIX_raw_profilo_{fdate}_{actual_time}.npy"
        np.save(os.path.join(save_path,profilo_mes_title),self.camera_measure)

