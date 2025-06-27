import importlib
import sys
import os

sys.path.append(f"..{os.sep}..{os.sep}")


class CameraBridge:
    """
    Allows to build a generic bridge based on a concrete one. Concrete
    bridge provides correct implementation regarding spectrometer model
    use. The generic bridge is an abstract layer that wrap concrete implementation.

    :param str spectro_name:
               Spectrometer concrete bridge implementation:

    :param float integration_time_ms:
               spectrometer integration time in milliseconds.
    """


class CameraBridge:
    def __init__(self, camera_name):
        try:
            class_name = f"{camera_name}Bridge"
            module_path = f"plugins.camera.{camera_name}.{class_name}"

            # import dynamique du module contenant la classe
            module = importlib.import_module(module_path)

            # récupération de la classe et instanciation
            class_obj = getattr(module, class_name)
            self.camera = class_obj()

        except Exception as e:
            raise Exception(f'Camera bridge "{camera_name}" could not be loaded: {e}')


    def camera_open(self):
        self.camera.init_camera()

    def get_image(self, tag=None, save_path=None):
        self.camera_open()
        self.image = self.camera.image_capture(tag, save_path)
        self.close_camera()



    def close_camera(self):
        self.camera.close()
