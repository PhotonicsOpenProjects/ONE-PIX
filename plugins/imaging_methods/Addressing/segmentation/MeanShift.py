import cv2
import numpy as np
from sklearn.cluster import MeanShift, estimate_bandwidth

class Clustering:

    def __init__(self, clustering_parameters=None):
        self.clustering_parameters = clustering_parameters or [2, 3]  # [unused, nombre_de_clusters]

    def get_clusters(self, IMG):
        print("begin Meanshifts segmentation")
        if len(self.clustering_parameters) < 2:
            raise ValueError("clustering_parameters doit contenir au moins deux valeurs.")

        desired_clusters = self.clustering_parameters[1]

        # Réduction taille pour rapidité
        img_small = cv2.resize(IMG, (IMG.shape[1] // 2, IMG.shape[0] // 2))
        flat = img_small.reshape(-1, 3)

        # Estimation de la bande passante
        bandwidth = estimate_bandwidth(flat, quantile=0.1, n_samples=500)
        ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
        ms.fit(flat)

        labels = ms.labels_
        n_clusters_found = len(np.unique(labels))
        print(f"[INFO] Mean Shift a trouvé {n_clusters_found} clusters")

        # Reshape labels → même taille que l'image
        labels_img = labels.reshape(img_small.shape[:2])
        labels_img = cv2.resize(labels_img, (IMG.shape[1], IMG.shape[0]), interpolation=cv2.INTER_NEAREST)

        # Garder les clusters les plus gros
        cluster_sizes = [(lab, np.sum(labels_img == lab)) for lab in np.unique(labels_img)]
        cluster_sizes = sorted(cluster_sizes, key=lambda x: -x[1])[:desired_clusters]
        selected_labels = [lab for lab, _ in cluster_sizes]

        # Création des masques
        masks = []
        for label in selected_labels:
            mask = np.uint8(labels_img == label) * 255
            masks.append(mask)

        return np.asarray(masks)
