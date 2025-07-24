import numpy as np
from datetime import date
from PIL import Image
import time
import os


class StubBridge:

    def __init__(self):
        # Obtenir le chemin absolu du dossier contenant ce script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "lena.jpg")

        try:
            # Charger et redimensionner l'image
            self.image = Image.open(image_path).convert("RGB")
            self.image = self.image.resize((1024, 768))  # Largeur x Hauteur
        except FileNotFoundError:
            print(f"Erreur : le fichier 'lena.jpg' est introuvable à l'emplacement : {image_path}")
            self.image = None

    def init_camera(self):
        pass


    def image_capture(self, tag, save_path):
        fdate = date.today().strftime("%d_%m_%Y")
        actual_time = time.strftime("%H-%M-%S")

        if tag == "init":
            save_path = f"./{tag}.png"
        elif save_path is None:
            save_path = f"./StubCam_{tag}_{fdate}_{actual_time}.png"

        if self.image:
            self.image.save(save_path)
        else:
            print("Impossible de capturer l'image : image non chargée.")

    def get_image_var(self):
        time.sleep(1)

    def close(self):
        pass
