from picamera import PiCamera, PiCameraError

class Raspicam:

    def __init__(self):
        self.camera = PiCamera(resolution = (1024, 768))
        self.camera.iso=300
        time.sleep(2)
        camera.shutter_speed = camera.exposure_speed
        camera.exposure_mode = 'off'
        g = camera.awb_gains
        camera.awb_mode = 'off'
        camera.awb_gains = g
        camera.vflip=True
        camera.hflip=True

    def image_capture(self):
        self_image=self.camera.capture(f"RGBCam_{fdate}_{actual_time}.jpg")
        

    def close(self):
        self.camera.close()