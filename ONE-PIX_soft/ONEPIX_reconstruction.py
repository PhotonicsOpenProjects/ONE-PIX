import numpy as np 
import matplotlib.pyplot as plt 
from src.DatacubeReconstructions import *
import src.datacube_analyse as hp


# Load raw data
acq_data=load_hypercube()
wl=acq_data['wavelengths']
datacube=acq_data['hyperspectral_image']


# Display spectral mean of the datacube
plt.figure()
plt.imshow(np.mean(datacube,2))
plt.show()

# Wavelengths cropping
borne_min=400
borne_max=800
datacube_rogn,wl_rogn=hp.clip_datacube(datacube,wl,borne_min,borne_max)


#Calculate RGB image from the raw datacube
rgb_image=hp.RGB_reconstruction(datacube_rogn,wl_rogn)
hp.select_disp_spectra(datacube_rogn,wl_rogn,3,'single')

# Reflectance normalisation
reflectance_datacube=hp.Flux2Ref(datacube_rogn,wl_rogn)
#Calculate RGB image from the normalised datacube
rgb_image=hp.RGB_reconstruction(reflectance_datacube,wl_rogn)
hp.select_disp_spectra(reflectance_datacube,wl_rogn,3,'single')
plt.title('Normalised reflectance RGB image')

# Kmeans clustering based on PCA
image_seg=hp.clustering(reflectance_datacube,components=3,n_cluster=5)
plt.figure()
plt.imshow(image_seg)
plt.title('Clustered image')

spec=hp.display_clust_spectra(image_seg,reflectance_datacube,wl_rogn)

