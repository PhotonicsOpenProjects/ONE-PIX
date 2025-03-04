from picamera import PiCamera, PiCameraError
import time
from datetime import date
import io
import numpy as np 
import time
from PIL import Image

class PicameraBridge:

    def __init__(self):
        pass

    def init_camera(self):
        self.camera = PiCamera(resolution=(1024, 768))
        self.camera.iso = 150
        time.sleep(1)
        self.camera.shutter_speed = self.camera.exposure_speed
        self.camera.exposure_mode = "off"
        g = self.camera.awb_gains
        self.camera.awb_mode = "off"
        self.camera.awb_gains = g
        self.camera.vflip = True
        self.camera.hflip = True
        print("Picamera is connected")

    def image_capture(self, tag, save_path):
        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time

        if tag == "init":
            save_path = f"./{tag}.png"
        elif save_path is None:
            save_path = f"PiCam_{tag}_{fdate}_{actual_time}.png"

        self.camera.capture(save_path)
        
    def get_image_var(self):
        """Capture l'image et la stocke dans une variable Python sous forme de tableau NumPy."""
        stream = io.BytesIO()
        self.camera.capture(stream, format='jpeg')
        stream.seek(0)
        img = Image.open(stream)
        self.image=np.mean(np.asarray(img),axis=2)
        time.sleep(1)
        return np.array(img)

    def close(self):
        self.camera.close()
