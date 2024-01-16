import os 
import sys
from xml.dom.domreg import well_known_implementations
sys.path.append(f'..{os.sep}..')
from core.Analysis import Analysis
import  plugins.imaging_methods.FIS_common_functions.FIS_common_analysis as ts

import matplotlib.pyplot as plt 
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import spectral as sp
import numpy as np 


an=Analysis() # creation of the anaysis class 
an.load_data()# loading of the hypercube by a tkinter windows 

fis=ts.FisAnalysis() # creating the specialize FIS analysis class for analysis of datacube 
rgb_image=fis.RGB_reconstruction(an.reconstructed_image,an.wavelengths) #  create a false rendering in RGB domain of the hyeprcube 
datacube=fis.datacube_normalisation_snv(an.reconstructed_image)
image_seg=fis.clustering(datacube,3,3) #  segmentation process using kmeans  with 3 clusters on the 3 first dimensions of PCA 



fig=plt.figure()
plt.suptitle("hyperspectral segmentation result")
plt.subplot(1,3,1)
plt.imshow(rgb_image)
plt.title("false RGB image of teh datacube")
plt.subplot(1,3,2)
plt.imshow(image_seg)
plt.title("hypercube segmented")


"""
plotting the result of the segmentation in the PCA domain 
"""
image_reshape=np.reshape(datacube,(np.size(datacube,0)*np.size(datacube,1),np.size(datacube,2)))
pca = PCA(3) 
principalComponents = pca.fit_transform(image_reshape)
kmeans = KMeans(3,n_init=11,random_state=0).fit(principalComponents)
kmeans.labels_


ax = fig.add_subplot(1,3,3,projection='3d')

ax.scatter(principalComponents[np.where(kmeans.labels_==0), 0], principalComponents[np.where(kmeans.labels_==0), 1], principalComponents[np.where(kmeans.labels_==0), 2],'r')
ax.scatter(principalComponents[np.where(kmeans.labels_==1), 0], principalComponents[np.where(kmeans.labels_==1), 1], principalComponents[np.where(kmeans.labels_==1), 2],'r')
ax.scatter(principalComponents[np.where(kmeans.labels_==2), 0], principalComponents[np.where(kmeans.labels_==2), 1], principalComponents[np.where(kmeans.labels_==2), 2],'r')

plt.title("datacube pixels in the PCA domain")
plt.show()
















