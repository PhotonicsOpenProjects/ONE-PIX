###############
API Reference
###############


.. _api:

The public api of ONE-PIX is provided allows to acquire hyperspectral datacubes using single pixel imaging.
The basic features to acquire a datacube are provided, for several spectrometer brands or patterns bases.

=======================================
Hyperspectral SPI acquisition
=======================================


Pattern Methods
------------------

Class allowing to use a specific pattern method.

.. automodule:: PatternMethods
   :members:

Acquisition
---------------
This class allows to set acquisition parameters to perform ONE-PIX acqusitions.

.. automodule:: AcquisitionConfig
   :members:

Spectrometer Selection
------------------------

This class is used to access spectrometer features.

.. automodule:: SpectrometerBridge
   :members:




====================================================
Hyperspectral SPI reconstruction and analysis
====================================================

Reconstruction
------------------
This class contains the set of methods to reconstruct datacubes according to the chosen acquisition method.

.. automodule:: DatacubeReconstructions
   :members:


Analysis
------------------
Library containing several methods to analyse datacube

.. automodule:: datacube_analyse
   :members: