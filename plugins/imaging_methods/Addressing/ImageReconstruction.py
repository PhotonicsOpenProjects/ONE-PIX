import numpy as np
import matplotlib.pyplot as plt
import cv2
import os
from onepix import utils as utils
from pathlib import Path
from datetime import date
import time
import orjson

class Reconstruction:

    def __init__(self,acquisition_dict):
        self.reconstruction_results={}

        self.reconstruction_results["spectra"] = np.asarray(acquisition_dict["spectra"])
        self.reconstruction_results["wavelengths"]=np.asarray(acquisition_dict["wavelengths"])
        self.reconstruction_results["cluster_name"] = acquisition_dict["patterns_order"]
        patterns_list = acquisition_dict["patterns"]  # liste de listes (JSON)
        masks = [np.array(mask) for mask in patterns_list]
        self.reconstruction_results["masks"] = masks

        self.reconstruction_results["rgb"]=np.asarray(acquisition_dict["rgb"])


    def image_reconstruction(self):
        pass

    def save_reconstructed_image( self, header, filename, save_path=None):
        save_path = Path(__file__).resolve().parent.parent.parent.parent / "measure"
        if os.path.isdir(save_path):
            pass
        else :
            os.mkdir(save_path)

        fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time
        folder_name = f"ONE-PIX_HAS_reconstruction_{fdate}_{actual_time}"
        os.mkdir(os.path.join(save_path,folder_name))

        results_filename = f"reconstruction_results_{fdate}_{actual_time}.json"
        with open(os.path.join(save_path, folder_name, results_filename), "wb") as f:
            f.write(
                orjson.dumps(
                    self.reconstruction_results,
                    option=orjson.OPT_SERIALIZE_NUMPY, 
                    default=utils.default
                )
            )
        pass


    def get_result_to_plot(self):
        self.reconstruction_results["result2plot"]=self.build_overlay_with_spectra()
        return  self.reconstruction_results["result2plot"]
    

    def build_overlay_with_spectra(self, alpha=0.5, colormap_fn=None, figsize=(6, 4)):
        """
        Construit une seule image RGB combinée :
        - à gauche : image + masques colorés
        - à droite : graphe des spectres
        Affichable directement avec plt.imshow(result)

        Retour : np.ndarray (H, W_combined, 3)
        """
        rgb=self.reconstruction_results["rgb"]
        masks=self.reconstruction_results["masks"]
        spectra=self.reconstruction_results["spectra"]
        wavelengths=self.reconstruction_results["wavelengths"]

        n = len(masks)
        h, w, _ = rgb.shape

        # --- Génération des couleurs ---
        if colormap_fn is not None:
            colors = colormap_fn(n + 1)[1:]
            colors = [tuple(np.array(c) / 255) for c in colors]
        else:
            cmap = plt.get_cmap("tab10")
            colors = [cmap(i % 10)[:3] for i in range(n)]

        # --- Crée l’overlay masqué ---
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        for i, mask in enumerate(masks):
            color = np.array(colors[i]) * 255
            overlay += (mask[..., None] > 0) * color.astype(np.uint8)
        blended = cv2.addWeighted(rgb.astype(np.uint8), 1 - alpha, overlay, alpha, 0)

        # --- Crée la figure matplotlib du graphe ---
        fig, ax = plt.subplots(figsize=figsize, dpi=100)
        for i in range(n):
            ax.plot(wavelengths, spectra[i], color=colors[i], alpha=0.9, label=f"Cluster {i+1}")
        ax.set_xlabel("wavelengths")
        ax.set_ylabel("Intensity")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.3)
        fig.tight_layout()

        # --- Convertit le graphe en image numpy ---
        fig.canvas.draw()
        graph_img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        graph_img = graph_img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        plt.close(fig)

        # --- Redimensionne le graphe à même hauteur ---
        graph_img = cv2.resize(graph_img, (w, h))

        # --- Concatène côte à côte ---
        combined = np.concatenate([blended, graph_img], axis=1)

        return combined

    

  

        


