# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 10:15:25 2025

@author: luguen
"""

import os
import sys
sys.path.append(f"..{os.sep}..")

import numpy as np
import matplotlib.pyplot as plt
from plugins.imaging_methods.Profilo.ImageReconstruction import ProfiloReconstruction
from plugins.imaging_methods.Profilo.ImageAnalysis import Analysis

rec=ProfiloReconstruction(r"S:\Alternants\En-Cours\2022 Lisa Uguen\microscope hyperspectral\Topographie\objet\profilo.npy")
hauteur=rec.reconstruction()
an=Analysis()
an.plot_reconstructed_image(hauteur)

