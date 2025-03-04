from picamera import PiCamera
import picamera.array
import time
import numpy as np
import cv2
import io
from PIL import Image
from datetime import date

class Picamera_profiloBridge:
    def __init__(self):
        self.camera = None

    def init_camera(self):
        """Initialise la caméra avec les bons paramètres"""
        self.camera = PiCamera()
        self.camera.resolution = (640, 480)
        self.camera.framerate = 21.26  # Adapté au projecteur
        self.camera.iso = 100
        self.camera.brightness = 50
        self.camera.contrast = 0
        self.camera.shutter_speed = 500  # Court pour éviter la saturation
        self.camera.exposure_mode = "off"

        # ✅ Balance des blancs fixe
        self.camera.awb_mode = "off"
        self.camera.awb_gains = (1.0, 1.0)

        time.sleep(2)  # Laisse le capteur se stabiliser
        print("✅ Picamera initialisée avec les paramètres du live.")

    def image_capture(self, tag, save_path=None):
        """Capture une image et la sauvegarde"""
        fdate = date.today().strftime("%d_%m_%Y")  # Date actuelle
        actual_time = time.strftime("%H-%M-%S")  # Heure actuelle

        if tag == "init":
            save_path = f"./{tag}.png"
        elif save_path is None:
            save_path = f"PiCam_{tag}_{fdate}_{actual_time}.png"

        self.camera.capture(save_path)
        print(f"📷 Image capturée : {save_path}")

    def get_image_var(self, N=20):
        """Capture une image en moyennant N acquisitions successives"""
        with picamera.array.PiRGBArray(self.camera, size=(640, 480)) as stream:
            img_stack = np.zeros((480, 640, 3), dtype=np.float32)  # Stocker les images en float

            for i in range(N):
                self.camera.capture(stream, format="bgr", use_video_port=True)
                img_stack += stream.array.astype(np.float32)  # Ajouter à la somme des images
                stream.truncate(0)  # Nettoyer le buffer pour la prochaine capture

            img_avg = (img_stack / N).astype(np.uint8)  # Moyenne des images et conversion en uint8
            print(f"📊 Max pixel value après moyennage: {np.max(img_avg)}")
            self.image=np.mean(np.asarray(img_avg),axis=2)
            return img_avg  # Retourne l'image moyennée sous forme de tableau NumPy

    def close(self):
        """Ferme proprement la caméra"""
        self.camera.close()
        print("❌ Picamera fermée proprement.")
