# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 10:15:25 2025

@author: luguen
"""

import numpy as np
import matplotlib.pyplot as plt

raw_data=np.load(r"S:\Alternants\En-Cours\2022 Lisa Uguen\microscope hyperspectral\Topographie\objet\profilo.npy")
plt.figure()
plt.imshow(raw_data[0,:,:])