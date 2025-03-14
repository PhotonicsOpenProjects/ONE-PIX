from core.hardware.HardwareConfig import *
from core.ImagingMethodBridge import *
import cv2
import os
import json
import time
import threading
import numpy as np
from tkinter import *
from tkinter.messagebox import askquestion
from datetime import date


class Acquisition:
    """
    Class OPConfig is used to set up ONE-PIX acquisitions

    :param str spectro_name:
                Spectrometer concrete bridge implementation:

    :param float integration_time_ms:
                spectrometer integration time in milliseconds.

    """

    def __init__(self):

        self.hardware_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"..{os.sep}conf",
            "hardware_config.json",
        )
        ## get software configuration
        with open(self.hardware_config_path) as f:
            hardware_dict = json.load(f)
        
        self.software_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"..{os.sep}conf",
            "software_config.json",
        )
        ## get software configuration
        with open(self.software_config_path) as f:
            software_dict = json.load(f)

        self.acquisition_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"..{os.sep}conf",
            "acquisition_parameters.json",
        )

        ## get software configuration
        with open(self.acquisition_config_path) as f:
            acquisition_dict = json.load(f)

        self.imaging_method_name = acquisition_dict["imaging_method"]
        self.spatial_res = acquisition_dict["spatial_res"]
        self.dynamic_tint=acquisition_dict["dynamic_tint"]
        self.normalisation_path=software_dict["normalisation_path"]
        self.normalisation=acquisition_dict["Normalisation"]
        self.width = hardware_dict["width"]
        self.height = hardware_dict["height"]

        self.imaging_method = ImagingMethodBridge(
            self.imaging_method_name, self.spatial_res, self.height, self.width
        )
        self.hardware = Hardware()
        self.is_init = False

    def init_measure(self):
        """
        This function allows to initialize the display window and the patterns to be displayed before the starts of threads.


        Parameters
        ----------
        config : class
            OPConfig class object.

        Returns
        -------
        config : class
        * actualised OPConfig class object.
        * self.pattern_lib.decorator.sequence : sequence of patterns
        """
        if not (self.is_init):
            try:
                self.imaging_method.creation_patterns()
                self.nb_patterns = len(self.imaging_method.patterns_order)
                self.hardware.hardware_initialisation()
                self.spectra = np.zeros(
                    (self.nb_patterns, len(self.hardware.spectrometer.wavelengths)),
                    dtype=np.float32,
                )
                self.est_duration = round(
                    (self.nb_patterns * (self.hardware.periode_mes+self.hardware.periode_pattern)) / (60 * 1000), 2
                )
                self.is_init = True
            except Exception as e:
                print(e)
                self.is_init = False
        else:
            pass


    def thread_acquisition(self, path=None, time_warning=True):
        """
        Runs the projection of a sequence of patterns and spectrometer measurements
        in free-running mode, using threads for parallel execution. The resulting hyperspectral 
        chronograms are processed to extract mean spectrums for each pattern.

        Parameters
        ----------
        path : str, optional
            File path to save the acquisition data (default is None).
        time_warning : bool, optional
            If True, a warning about the estimated acquisition duration will be shown before starting (default is True).

        Returns
        -------
        None
            The method updates the object's state with the acquired spectra and metadata.
        """

        self.init_measure()
        
        # Show time warning if necessary
        if time_warning:
            ans = askquestion(message=f"Estimated acquisition duration: {self.est_duration} min")
            if ans != "yes":
                cv2.destroyAllWindows()
                return  # Exit early if the user doesn't confirm the acquisition

        # Begin acquisition process
        begin_acq = time.time()
        
        # Threads initialization
        event = threading.Event()
        
        # Define threads for pattern projection and spectrometer measurement
        patterns_thread = threading.Thread(
            target=self.hardware.projection.thread_projection,
            args=(
                event,
                self.imaging_method.patterns,
                self.imaging_method.patterns_order,
                self.imaging_method.pattern_creation_method.interp_method,
            )
        )
        
        spectrometer_thread = threading.Thread(
            target=self.hardware.spectrometer.thread_singlepixel_measure,
            args=(event, self.spectra,self.dynamic_tint)
        )

        try:
            # Start threads
            patterns_thread.start()
            spectrometer_thread.start()

            # Wait for threads to complete
            patterns_thread.join()
            spectrometer_thread.join()

            # Retrieve data after the threads finish
            self.spectra = self.hardware.spectrometer.spectra
            self.duration = time.time() - begin_acq
            self.create_acquisition_header()

        except Exception as e:
            # Handle any potential errors during the acquisition process
            print(f"An error occurred during acquisition: {e}")
            cv2.destroyAllWindows()

        finally:
            self.is_init = False

    def create_acquisition_header(self):
        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        # Header
        self.title_param = f"raw_acquisition_parameters_{fdate}_{actual_time}.txt"
        self.header = (
            f"ONE-PIX_raw_acquisition_{fdate}_{actual_time}"
            + "\n"
            + "--------------------------------------------------------"
            + "\n"
            + "\n"
            + f"Imaging method: {self.imaging_method_name}"
            + "\n"
            + "Acquisition duration: %f s" % self.duration
            + "\n"
            + f"Spectrometer {self.hardware.name_spectro} : {self.hardware.spectrometer.DeviceName}"
            + "\n"
            + f"Camera: {self.hardware.name_camera}"
            + "\n"
            + "Number of projected patterns: %d" % self.nb_patterns
            + "\n"
            + "Height of pattern window: %d pixels" % self.height
            + "\n"
            + "Width of pattern window: %d pixels" % self.width
            + "\n"
            + "Number of spectral measures per pattern: %d  " % self.hardware.repetition
            + "\n"
            + "Integration time: %d ms" % self.hardware.spectrometer.integration_time_ms
            + "\n"
        )

    def save_raw_data(self, path=None):
        self.imaging_method.pattern_creation_method.save_raw_data(self)
        
