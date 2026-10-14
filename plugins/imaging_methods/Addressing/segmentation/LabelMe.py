from labelme.label_file import LabelFile
import labelme.utils
import numpy as np
import cv2
import os
from datetime import date
import time


class Clustering:

    def __init__(self, clustering_parameters):
        self.clustering_parameters = clustering_parameters
        self.patterns_order = []

    def label2mask(self, json_file):

        label_file = LabelFile(json_file)
        img = labelme.utils.img_data_to_arr(label_file.imageData)

        label_name_to_value = {"_background_": 0}

        for shape in sorted(label_file.shapes, key=lambda x: x["label"]):
            label_name = shape["label"]
            self.patterns_order.append(label_name)
            if label_name in label_name_to_value:
                label_value = label_name_to_value[label_name]
            else:
                label_value = len(label_name_to_value)
                label_name_to_value[label_name] = label_value
        lbl, _ = labelme.utils.shapes_to_label(
            img.shape, label_file.shapes, label_name_to_value
        )

        self.nb_clust = len(label_name_to_value)
        value_in_lbl = np.unique(lbl)

        masks = []
        for value in value_in_lbl:
            idx = np.where(lbl == value)
            mask = np.zeros(np.shape(lbl))
            mask[idx] = 255
            masks.append(mask)

        masks = np.asarray(masks)
        return masks

    def get_clusters(self, img):
        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        image_name = f"img_{fdate}_{actual_time}.jpg"
        cv2.imwrite(image_name, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        os.system("labelme " + image_name + " -O " + image_name[:-4] + ".json")
        json_file = image_name[:-4] + ".json"
        masks = self.label2mask(json_file)

        os.remove(json_file)
        os.remove(image_name)
        return masks
