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

rec=ProfiloReconstruction(r"C:\Users\grussias\Desktop\repo git\Photonics_bretagne\profilo.npy")
depth_map=rec.reconstruction()

plt.figure()
plt.imshow(depth_map)
plt.show()