from pypylon import pylon
import os
from datetime import date
import time

class BaslerCameraBridge:

    def __init__(self):
        pass

    def init_camera(self):
        try:
            # Création d'une instance de caméra
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.camera.Open()
            
            # Configuration par défaut de la caméra
            self.camera.Width.Value = min(1024, self.camera.Width.Max)
            self.camera.Height.Value = min(768, self.camera.Height.Max)
            self.camera.OffsetX.Value = 0
            self.camera.OffsetY.Value = 0
            self.camera.ExposureTime.SetValue(20000.0)  # Exemple d'exposition en microsecondes
            self.camera.Gain.SetValue(0.0)             # Gain minimal
            
            print("Pylon camera is connected and initialized.")
        except Exception as e:
            print(f"Error initializing Pylon camera: {e}")

    def image_capture(self, tag, save_path):
        try:
            fdate = date.today().strftime("%d_%m_%Y")
            actual_time = time.strftime("%H-%M-%S")

            # Définir le chemin d'enregistrement par défaut si nécessaire
            if tag == "init":
                save_path = f"./{tag}.png"
            elif save_path is None:
                save_path = f"PylonCam_{tag}_{fdate}_{actual_time}.png"

            # Capture d'une image
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if grab_result.GrabSucceeded():
                # Convertir l'image en format compatible OpenCV (BGR8)
                converter = pylon.ImageFormatConverter()
                converter.OutputPixelFormat = pylon.PixelType_BGR8packed
                image = converter.Convert(grab_result)

                # Sauvegarde de l'image
                img_array = image.GetArray()
                import cv2
                cv2.imwrite(save_path, img_array)
                print(f"Image saved to {save_path}")

            grab_result.Release()
            self.camera.StopGrabbing()

        except Exception as e:
            print(f"Error capturing image: {e}")

    def close(self):
        try:
            if self.camera.IsOpen():
                self.camera.Close()
            print("Pylon camera is disconnected.")
        except Exception as e:
            print(f"Error closing Pylon camera: {e}")
