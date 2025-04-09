import cv2
import numpy as np
from skimage.filters import threshold_multiotsu

class Clustering:

    def __init__(self, clustering_parameters=None):
        self.clustering_parameters = clustering_parameters or [2, 3]

    def get_clusters(self, IMG):
        if len(self.clustering_parameters) < 2:
            raise ValueError("clustering_parameters doit contenir au moins deux valeurs.")
        
        nb_clusters = self.clustering_parameters[1]

        # Convertir en niveaux de gris
        gray = cv2.cvtColor(IMG, cv2.COLOR_BGR2GRAY)

        # Appliquer multi-Otsu
        thresholds = threshold_multiotsu(gray, classes=nb_clusters)
        regions = np.digitize(gray, bins=thresholds)

        # Créer un masque pour chaque classe
        masks = [(regions == i).astype(np.uint8) * 255 for i in range(nb_clusters)]

        return np.asarray(masks)
