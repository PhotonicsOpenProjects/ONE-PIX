###############
API Reference
###############

The public api of ONE-PIX allows to acquire hyperspectral datacubes using single pixel imaging.
The basic features to acquire a datacube are provided, for several spectrometer brands or patterns bases.

=======================================
Hyperspectral SPI acquisition
=======================================

Imaging methods
------------------

Class allowing to use a specific pattern method.

.. automodule:: ImagingMethodBridge
   :members:


Acquisition
---------------
This class allows to set acquisition parameters to perform ONE-PIX acqusitions.

.. automodule:: Acquisition
   :members:


====================================================
Hyperspectral SPI reconstruction and analysis
====================================================

Reconstruction
------------------
This class contains the set of methods to reconstruct datacubes according to the chosen acquisition method.

.. automodule:: Reconstruction
   :members:

Analysis
------------------
Library containing several methods to analyse datacube

.. automodule:: Analysis
   :members:
