import numpy as np 

class StubBridge:

    def __init__(self):
        print("stub camera connected")


    def image_capture(self):
        self.image=255*np.random.rand(1920,1080)
        

    def close(self):
        print("stub camera disconnected")