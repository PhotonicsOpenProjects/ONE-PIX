import importlib
import numpy as np
import time
import warnings
import cv2

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

    def get_optimal_integration_time(self, verbose=True):
        """
        This function automatically sets the optimal integration time for
        ONE-PIX acquisitions based on the measurable optical flux.
    
        Parameters
        ----------
        verbose : bool, optional
            If True, print the details of each step (default is True).
    
        Returns
        -------
        int
            Optimal integration time in milliseconds.
        """
        repetitions = 2
        max_counts = 30000
        tolerance = 2500
        max_iterations = 10
        max_integration_time = 10000  # Maximum 10 seconds (10000 ms)
        min_integration_time = 1      # Minimum 1 millisecond
    
        self.set_integration_time()
        delta_wl = round(0.05 * np.size(self.get_wavelengths()))
        count = 0
    
        while True:
            measurements = []
            for _ in range(repetitions):
                measurements.append(self.get_intensities())
    
            # Calculate mean of measurements and exclude the edges defined by delta_wl
            mean_measurement = np.mean(np.array(measurements), axis=0)[delta_wl:-delta_wl]
            peak_intensity = max(mean_measurement)
            delta_intensity = peak_intensity - max_counts
    
            if verbose:
                print(f"T{count}={self.integration_time_ms} ms with intensity peak at {round(peak_intensity)} counts")
    
            # Check if the peak intensity is within the tolerance range
            if abs(delta_intensity) < tolerance:
                break
    
            # Stop if max iterations are reached
            if count >= max_iterations:
                warnings.warn(f"Stopped after {count} iterations. Final integration time: {self.integration_time_ms} ms.")
                break
    
            # Adjust integration time based on the intensity ratio
            adjustment_factor = max_counts / peak_intensity
            self.integration_time_ms = int(self.integration_time_ms * adjustment_factor)
    
            # Handle limits: force integration time between 1 ms and 1 second (1000 ms)
            if self.integration_time_ms < min_integration_time:
                self.integration_time_ms = min_integration_time
            elif self.integration_time_ms > max_integration_time:
                self.integration_time_ms = 1000  # Force to 1 second if it exceeds 10 seconds
    
            # Apply the new integration time
            self.set_integration_time()
            count += 1
    
        # Reset spectro_flag and display final integration time
        self.spectro_flag = False
        if verbose:
            print(f"Final integration time (ms): {self.integration_time_ms}")
        cv2.destroyAllWindows()
        return self.integration_time_ms

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
