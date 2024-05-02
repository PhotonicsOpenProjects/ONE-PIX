import numpy as np
from datetime import date
from PIL import Image
import time


class StubBridge:

    def __init__(self):
        pass

    def init_camera(self):
        print("stub camera connected")

    def image_capture(self, tag, save_path):
        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        if tag == "init":
            save_path = f"./{tag}.png"
        elif save_path is None:
            save_path = f"./StubCam_{tag}_{fdate}_{actual_time}.png"

        self.image = Image.fromarray(np.uint8((255 * np.random.rand(768, 1024))))
        self.image.save(save_path)

    def close(self):
        print("stub camera disconnected")
