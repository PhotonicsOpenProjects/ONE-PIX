import importlib
import numpy as np
import time


class SpectrometerBridge:
    """
    Allows to build a generic bridge based on a concrete one. Concrete
    bridge provides correct implementation regarding spectrometer model
    use. The generic bridge is an abstract layer that wrap concrete implementation.

    :param str spectro_name:
               Spectrometer concrete bridge implementation:

    :param float integration_time_ms:
               spectrometer integration time in milliseconds.
    """

    def __init__(self, spectro_name, integration_time_ms, wl_lim, repetition):
        # Concrete spectrum implementation dynamic instanciation
        try:
            module_name = f"plugins.spectrometer.{spectro_name}."
            className = spectro_name + "Bridge"
            module = importlib.import_module(module_name + className)
            classObj = getattr(module, className)
            self.spectrometer = classObj(integration_time_ms)
            self.wl_lim = wl_lim
            self.repetition = repetition
        except ModuleNotFoundError:
            raise Exception(
                'Concrete bridge "'
                + spectro_name
                + '" implementation has not been found.'
            )

        # Misc
        self.DeviceName = ""
        self.integration_time_ms = integration_time_ms

    def spec_open(self):
        self.spectrometer.spec_open()
        self.DeviceName = self.spectrometer.DeviceName
        wavelengths = self.spectrometer.get_wavelengths()
        self.idx_wl_lim = [
            np.abs(wavelengths - self.wl_lim[0]).argmin(),
            np.abs(wavelengths - self.wl_lim[1]).argmin(),
        ]

    def set_integration_time(self):
        self.spectrometer.integration_time_ms = self.integration_time_ms
        self.spectrometer.set_integration_time()

    def get_wavelengths(self):
        self.wavelengths = self.spectrometer.get_wavelengths()[
            self.idx_wl_lim[0] : self.idx_wl_lim[1]
        ]
        return self.wavelengths

    def get_intensities(self):
        spectrum = self.spectrometer.get_intensities()[
            self.idx_wl_lim[0] : self.idx_wl_lim[1]
        ]
        return spectrum

    def spec_close(self):
        self.spectrometer.spec_close()

    def get_optimal_integration_time(self):
        """
        This function allows to automatically set the right integration time for
        ONE-PIX acqusitions depending on the mesurable optical flux.

        Parameters
        ----------
        config : class
            OPConfig class object.

        Returns
        -------
        None. Actualisation of the integration_time_ms parameter of config

        """
        repetitions = 5
        max_counts = 30000
        self.set_integration_time()

        flag = True
        self.spectro_flag = True
        count = 0
        delta_wl = round(0.05 * np.size(self.get_wavelengths()))
        while flag:
            mes = []
            for acq in range(repetitions):
                mes.append(self.get_intensities())
            mes = np.mean(np.array(mes), 0)[delta_wl:-delta_wl]
            delta = max(mes) - max_counts
            print(
                f"Tint{count}={self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts"
            )

            if abs(delta) < 2500:
                flag = False
            elif self.integration_time_ms >= 10e3 or self.integration_time_ms == 0:
                flag = False
                self.spec_close()
                self.integration_time_ms = 1
                print(
                    Exception(
                        f"Integration time: {self.integration_time_ms} ms, if you want to continue set the parameter by hand"
                    )
                )

            elif count >= 10:
                flag = False
                print(
                    f"Measures stopped after {count} iterations. Integration time= {self.integration_time_ms} ms with intensity peak at {round(max(mes))} counts"
                )
            else:
                count += 1
                flag = True
                coeff = max_counts / max(mes)
                self.integration_time_ms = int(self.integration_time_ms * coeff)
                self.integration_time_ms = self.integration_time_ms
                self.set_integration_time()

            self.set_integration_time()
            self.spectro_flag = False
        print(f"Integration time (ms): {self.integration_time_ms}")

    def thread_singlepixel_measure(self, event, spectra, dynamic_tint=False):
        """
        Synchronises spectrometer acquisition with pattern display, measuring spectra
        in response to the event signal. Results are stored in the provided spectra array.

        Parameters
        ----------
        event : threading.Event
            Event that indicates when a pattern is displayed and synchronises the measurement.
        spectra : np.ndarray
            2D array where measured spectra will be stored.
        dynamic_tint : bool, optional
            If True, dynamically adjust the spectrometer's integration time (default is False).

        Returns
        -------
        None
        """

        # Initial validation
        if spectra is None or not isinstance(spectra, np.ndarray):
            raise ValueError("The spectra parameter must be a valid NumPy array.")

        try:
            cnt = 0
            self.spectra = spectra
            nb_patterns = np.size(spectra, 0)
            coeff = 1  # Coefficient to adjust for integration time scaling
            integration_times = []  # List to store the integration times for each pattern
            while cnt < nb_patterns:
                if event.is_set():  # Event set when a pattern is displayed
                    if dynamic_tint and cnt < nb_patterns - 1:
                        # Adjust integration time for all patterns except the last one
                        self.get_optimal_integration_time()
                        # Store the current integration time for future use (last pattern)
                        integration_times.append(self.integration_time_ms)

                        # Measure intensities for the current pattern
                        chronograms = []
                        for _ in range(self.repetition):
                            intensities = self.get_intensities()
                            if intensities is None:
                                raise RuntimeError("Failed to retrieve intensities from the spectrometer.")
                            chronograms.append(coeff * intensities)
                        # Average the measurements and store the result in spectra
                        self.spectra[cnt, :] = np.mean(chronograms, axis=0) / self.integration_time_ms
                    
                    elif dynamic_tint and cnt==nb_patterns-1:
                        # Last iteration: Measure the dark image for each previously used integration time
                        print("Measuring dark images for all previous integration times.")

                        dark_spectra = np.zeros_like(self.spectra)  # Array to store dark spectra for each pattern

                        for i, tint in enumerate(integration_times):
                            print(f"Measuring dark spectrum for pattern {i+1} with integration time {tint} ms.")
                            self.integration_time_ms = tint  # Set the same integration time as during the pattern acquisition
                            self.set_integration_time()
                            chronograms_dark = []
                            for _ in range(self.repetition):
                                dark_intensities = self.get_intensities()  # Measure the dark image
                                if dark_intensities is None:
                                    raise RuntimeError("Failed to retrieve dark image intensities.")
                                chronograms_dark.append(dark_intensities)

                            # Average the dark measurements
                            dark_spectra[i, :] = np.mean(chronograms_dark, axis=0) / tint

                        # Subtract the dark spectra from the measured spectra
                        self.spectra -= dark_spectra
                        print("Dark spectrum subtraction complete.")
                    
                    else: # Measure without dynamic integration time
                        # Measure intensities for the current pattern
                        chronograms = []
                        for _ in range(self.repetition):
                            intensities = self.get_intensities()
                            if intensities is None:
                                raise RuntimeError("Failed to retrieve intensities from the spectrometer.")
                            chronograms.append(coeff * intensities)
                        # Average the measurements and store the result in spectra
                        self.spectra[cnt, :] = np.mean(chronograms, axis=0) / self.integration_time_ms
                    
                    cnt += 1
                    event.clear()  # Clear event to wait for the next pattern
                else:
                    # Small sleep to avoid busy waiting
                    time.sleep(1e-6)

            
        except Exception as e:
            # Log error for debugging
            print(f"An error occurred during spectrometer acquisition: {e}")

        finally:
            # Ensure the spectrometer is closed properly
            self.spec_close()
