###############
API Reference
###############


.. _api:

The public api of `seabreeze` is provided by the `seabreeze.spectrometers` submodule.
The basic features to acquire a spectrum are provided for all spectrometer models independent
of the backend.

=======================================
Hyperspectral SPI acquisition
=======================================


Pattern Methods
------------------

Provides a list of available instances of `SeaBreezeDevice`

.. automodule:: PatternMethods
   :members:

Spectrometer Selection
------------------------

The `Spectrometer` class is used to access spectrometer features.

.. automodule:: SpectrometerBridge
   :members:


Acquisition
------------------------
.. automodule:: AcquisitionConfig
   :members:

====================================================
Hyperspectral SPI reconstruction and analysis
====================================================



Reconstruction
------------------
.. automodule:: DatacubeReconstructions
   :members:


Analysis
------------------
.. automodule:: datacube_analyse
   :members: