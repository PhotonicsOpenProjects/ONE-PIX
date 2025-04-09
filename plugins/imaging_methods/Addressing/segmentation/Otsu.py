import cv2
import numpy as np

class Clustering:

    def __init__(self, clustering_parameters=None):
        self.clustering_parameters = clustering_parameters or [2]

    def get_clusters(self, IMG):
        desired_clusters = self.clustering_parameters[0]
        gray = cv2.cvtColor(IMG, cv2.COLOR_BGR2GRAY)

        # Chaque élément de la pile : (image_segment, mask associé)
        stack = [(gray, np.ones_like(gray, dtype=bool))]

        masks = []

        while len(masks) < desired_clusters and stack:
            region, region_mask = stack.pop(0)

            # Appliquer Otsu sur cette région uniquement
            try:
                _, thresh = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            except:
                # Si Otsu plante (image uniforme), on garde le masque tel quel
                masks.append(region_mask)
                continue

            mask1 = (region < _) & region_mask
            mask2 = (region >= _) & region_mask

            if np.any(mask1):
                stack.append((region * mask1, mask1))
            if np.any(mask2):
                stack.append((region * mask2, mask2))

            # Si on ne peut plus splitter, on stoppe
            if len(stack) + len(masks) >= desired_clusters:
                break

        # On convertit tous les masques restants en uint8
        masks += [m for _, m in stack]
        masks = masks[:desired_clusters]  # garde seulement le nombre demandé

        final_masks = []
        for m in masks:
            mask_uint8 = np.uint8(m) * 255
            final_masks.append(mask_uint8)

        return np.asarray(final_masks)
