===================
Contributing Guide
===================
If you want to contribute to ONE-PIX kit, please create a pull request on Github.
Documentation improvements are very welcome!
Extending ONE-PIX kit can be performed in several ways. Look at the guides below.

.. tip::

    You can pull request your contributions and their associated documentation.

.. note::
    If you are not familiar with Github, you can find more information by following this `link <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/about-collaborative-development-models>`_. 

Adding a new spectrometer
-------------------------

To add a new spectrometer device with basic spectrometer Python functionalities, you need to 
get its API necessary informations to open and close the communication with the device, get spectra 
intensities and sampled wavelengths and set the integration times.


Add a new spectrometer class python file to `ONE-PIX/plugins/spectrometer` with the folder name:
<Spectrometer_name>. In this folder create a python class file named <Spectrometer_name>Bridge.py. 
This folder will also be the location where every needed library to run spectral measures must be in.


..  code:: python
	
	class Spectrometer_nameBridge:
			
		def __init__(self,integration_time_ms):
			self.integration_time_ms=integration_time_ms
			self.spec=[]
			self.DeviceName=''
				
		def spec_open(self):
			# commands to initiate the communication with the spectrometer

		def set_integration_time(self):
			# commands to set the integration time in milliseconds self.integration_time_ms

		def get_wavelengths(self):
			# commands to get sampled wavelengths
			return wavelengths
			
		def get_intensities(self):
			# commands to get spectra intensities
			return intensities
		
		def spec_close(self):
			# commands to end the communication with the spectrometer

Fulfilling these lines allows to use your device with the ONE-PIX kit.


Adding a new pattern basis or method 
-----------------------------------------

You can also add new pattern bases or new methods for hyperspectral compressive imaging.
To do so, create a new folder <Pattern_method> in `ONE-PIX_soft/plugins/imaging_methods`.

In this folder, you must then buil three different classes for patterns creation, data reconstruction and data analysis strictly named :
"PatternsCreation.py", "ImageReconstruction.py" and "ImageAnalysis.py".

The formats of the following classes to be created are explained below:

"PatternsCreation.py"

..  code:: python
	
	class PatternsCreation:
	
		def sequence_order(self):
			# create a list of string describing the name of the patterns 
			return pattern_order,...

		def creation_sequence(self):
			# create the sequence(s) to be projected
			return sequence

		
"ImageReconstruction.py"

..  code:: python
	
	class ImageReconstruction:
	
		def __init__(self,spectra,pattern_order):
			self.spectra=spectra
			self.pattern_order=pattern_order
			
		def spectrum_reconstruction:
			# allows to transform raw data into well shaped spectral datacube in spatial frequencies domain
			return spectrum
			
		def datacube_reconstruction(self):
			# use spectrum reconstrum first and then apply your method to reconstruct an image datacube
			return spectrum,datacube

			
"ImageAnalysis.py"

..  code:: python
	
	class ImageAnalysis:
	
		def __init__(self,data_path=None):
			self.data_path=data_path
			
		def load_reconstructed_data(self,data_path=None):
			# Method to load data produced by the methods described before. You must fulfill the way of getting reconstructed_data and wavelengths to the class.
			#self.reconstructed_data=
			#self.wavelengths=
		def data_normalisation(self,ref_datacube):
			#allows to specify how to normalise your data using reflectance
			#normalised_data=
			return normalised_data

		def get_rgb_image(self,datacube,wavelengths):
			# if relevant, mehod to build RGB image from reconstructed data, else pass
			#rgb_image=
			return rgb_image
		
		def plot_reconstructed_image(self,datacube,wavelengths):
			# Design a typical plot to display after data reconstruction
			
        