from xml.dom.domreg import well_known_implementations
from onepix.Analysis import Analysis
import plugins.imaging_methods.FIS_common_functions.FIS_common_analysis as ts

import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import spectral as sp
import numpy as np


an = Analysis()  # creation of the anaysis class
an.load_data()  # loading of the hypercube by a tkinter windows


fis = (
    ts.FisAnalysis()
)  # creating the specialize FIS analysis class for analysis of datacube


rgb_image = an.get_rgb_image(
    an.reconstructed_data, an.wavelengths
)  #  create a false rendering in RGB domain of the hyeprcube

datacube = fis.datacube_normalisation_snv(an.reconstructed_data)

an.save_analysed_image("test_save_an","../Hypercubes")


