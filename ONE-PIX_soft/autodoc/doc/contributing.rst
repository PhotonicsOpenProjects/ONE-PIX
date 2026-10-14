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


Add a new spectrometer class python file to `ONE-PIX_soft/src/spectrometer_bridges` with the file name:
<Spectrometer_name>Bridge.py

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

You can also add new pattern bases or new methods for hyperspectral compressive imaging:
Add a new pattern method class python file to `ONE-PIX_soft/src/pattern_bases` with the file name:
<Pattern_method>Basis.py

..  code:: python
	
	class Pattern_methodBasis:
	
		def sequence_order(self):
			# create a list of string describing the name of the patterns 
			return pattern_order,...

		def creation_sequence(self):
			# create the sequence(s) to be projected
			return sequence

		
Adding a new reconstruction method
-----------------------------------------

Finally, if needed, you can add a reconstruction method to transform your acquisitions made from 
a new basis.

To do so, add a new reconstruction method class python file to `ONE-PIX_soft/src/reconstruction_methods` with the file name:
<Reconstruction_method>Reconstruction.py

..  code:: python
	
	class Pattern_methodBasis:
	
		def __init__(self,spectra,pattern_order):
			self.spectra=spectra
			self.pattern_order=pattern_order
			
		def spectrum_reconstruction:
			# allows to transform raw data into well shaped spectral datacube in spatial frequencies domain
			return spectrum
			
		def datacube_reconstruction(self):
			# use spectrum reconstrum first and then apply your method to reconstruct an image datacube
			return spectrum,datacube

			
