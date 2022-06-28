# -*- coding: utf-8 -*-
"""
Created on Wed Dec  1 10:53:44 2021

@author: mribes
"""

import numpy as np 
import matplotlib.pyplot as plt 
from src.DatacubeReconstructions import *
import src.datacube_analyse as hp


# Load raw data
acq_data=load_spectra()
wl=acq_data['wavelengths']
spectra=acq_data['spectra']

# ONEPIX datacube reconstruction
res=OPReconstruction(acq_data['pattern_method'],spectra,acq_data['pattern_order'])
res.Selection()
res=hp.spikes_correction(res)

# Display spectral mean of the datacube
plt.figure()
plt.subplot(1,2,1)
plt.imshow(np.log10(abs(np.mean(res.whole_spectrum,2))))

plt.subplot(1,2,2)
plt.imshow(np.mean(res.hyperspectral_image,2))
plt.show()
# Wavelengths cropping
borne_min=400
borne_max=800
res.hyperspectral_image_rogn,wl_rogn=hp.clip_datacube(res.hyperspectral_image,wl,borne_min,borne_max)


#Calculate RGB image from the raw datacube
rgb_image=hp.RGB_reconstruction(res.hyperspectral_image_rogn,wl_rogn)
hp.select_disp_spectra(res.hyperspectral_image_rogn,wl_rogn,3,'single')

# Reflectance normalisation
res.reflectance_datacube=hp.Flux2Ref(res.hyperspectral_image_rogn,wl_rogn)
#Calculate RGB image from the normalised datacube
rgb_image=hp.RGB_reconstruction(res.reflectance_datacube,wl_rogn)
hp.select_disp_spectra(res.reflectance_datacube,wl_rogn,3,'single')
plt.title('Normalised reflectance RGB image')

# Kmeans clustering based on PCA
image_seg=hp.clustering(res.reflectance_datacube,components=3,n_cluster=5)
plt.figure()
plt.imshow(image_seg)
plt.title('Clustered image')

spec=hp.display_clust_spectra(image_seg,res.reflectance_datacube,wl_rogn)

