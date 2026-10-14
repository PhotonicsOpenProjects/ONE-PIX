import sys
import os
import screeninfo
import numpy as np

sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../.."))

from AcquisitionConfig import *


class OPTest:
    def __init__(self, json_path) -> None:
        self.json_path = json_path

    def is_picam_running(self):
        if is_raspberrypi():
            try:
                import picamera

                camera = picamera.PiCamera()
                test = True
            except:
                test = False
        else:
            test = False

        return test

    def is_spectrometer_running(self):
        test = False
        try:
            config = OPConfig(self.json_path)
            config.spec_lib.spec_open()
            config.spec_lib.set_integration_time_ms()
            wl = config.spec_lib.get_wavelengths()
            spectrum = config.spec_lib.get_intensities()
            if np.logicaland(wl != [], spectrum != []):
                test = True
            config.spec_lib.spec_close()
        except:
            test = False

        return test

    def is_projector_running(self):
        try:
            proj_shape = screeninfo.get_monitors()[1]
            test = True
        except IndexError:
            test = False
        return test


if __name__ == "__main__":
    json_path = "../../acquisition_param_ONEPIX.json"
    tests = OPTest(json_path)
    methods = dir(tests)
    filt_methods = [k for k in methods if "__" not in k]
    filt_methods.remove("json_path")
    print("\n")
    print("----- ONE-PIX TESTS RUNNING -----")
    print("\n")
    for test in filt_methods:
        print("TEST: " + test + " :" + str(eval(f"tests.{test}()")))
