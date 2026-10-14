import cv2
import numpy as np
from skimage.segmentation import slic
from skimage.util import img_as_float

class Clustering:

    def __init__(self, clustering_parameters=None):
        self.clustering_parameters = clustering_parameters or [2, 100]  # [unused, n_clusters]

    def get_clusters(self, IMG):
        if len(self.clustering_parameters) < 2:
            raise ValueError("clustering_parameters doit contenir au moins deux valeurs.")

        n_segments = self.clustering_parameters[1]

        # SLIC attend une image float [0, 1]
        img_float = img_as_float(cv2.cvtColor(IMG, cv2.COLOR_BGR2RGB))

        # Appliquer SLIC
        labels = slic(img_float, n_segments=n_segments, start_label=0)

        # Générer un masque par cluster (superpixel)
        unique_labels = np.unique(labels)
        masks = [(labels == label).astype(np.uint8) * 255 for label in unique_labels]

        return np.asarray(masks)
