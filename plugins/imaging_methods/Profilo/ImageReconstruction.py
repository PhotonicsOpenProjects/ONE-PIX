import os
import sys
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append('..')
import cv2
import scipy.ndimage as ndimage
import numpy as np
from skimage.restoration import unwrap_phase
import matplotlib.pyplot as plt
from core.hardware.coregistration_lib import *

class ProfiloReconstruction:

    def __init__(self,raw_mesure=None):
        if type(raw_mesure)==str:
            self.raw_measure=np.load(raw_mesure)
        else:
            self.raw_measure=raw_mesure

        screen_resolution=(800,600)
        self.rect = post_coregistration_calibration(self.raw_measure[0,:,:],screen_resolution)
        self.raw_measure=self.apply_corregistration(self.raw_measure)

    def apply_corregistration(self,raw_measure):

        img_wrap=apply_corregistration(raw_measure[0,:,:])
        imgs_wrap=np.zeros((np.shape(raw_measure)[0],np.shape(img_wrap)[0],np.shape(img_wrap)[1]))

        for i in range(np.shape(raw_measure)[0]):
            imgs_wrap[i,:,:]=apply_corregistration(raw_measure[i,:,:])
        
        return imgs_wrap
    

    def get_z_from_raw(self,raw_measure):
        Num = raw_measure[3].astype(float) - raw_measure[1].astype(float)
        Den = raw_measure[0].astype(float) - raw_measure[2].astype(float)
        PHI = np.arctan2(Num, Den)
        ZOBJ = unwrap_phase(PHI)

        Num2 = self.raw_measure[7].astype(float) - self.raw_measure[5].astype(float)
        Den2 = self.raw_measure[4].astype(float) - self.raw_measure[6].astype(float)
        PHI2 = np.arctan2(Num2, Den2)

        ZOBJ = unwrap_phase(PHI)
        ZOBJ2 = unwrap_phase(PHI2)

        ZOBJ_moy=np.mean([ZOBJ, ZOBJ2], axis=0)
        return ZOBJ_moy

    def load_reference(self,ref_path):
        self.reference_raw=np.load(ref_path)
        self.reference_raw=self.apply_corregistration(self.reference_raw)
        



    def reconstruction_with_ref(self):
        self.reference= self.get_z_from_raw(self.reference_raw)
        ZOBJ_moy= self.get_z_from_raw(self.raw_measure)
        depth=ZOBJ_moy-self.reference
        return depth
        
    def select_4_points(self,depth_map):
        """
        Affiche la depth map et permet de sélectionner 4 points.
        Retourne les coordonnées (x, y, z) des 4 points.
        
        :param depth_map: np.array 2D contenant la carte de profondeur
        :return: np.array de shape (4,3) avec (x, y, z)
        """
        plt.figure(figsize=(8, 6))
        plt.imshow(depth_map, cmap='jet')
        plt.colorbar(label="Profondeur")
        plt.title("Cliquez sur 4 points et appuyez sur Entrée")

        # Sélectionner 4 points avec la souris
        points = np.array(plt.ginput(4, timeout=0))  # (x, y) récupérés en float
        plt.close()  # Ferme la fenêtre après la sélection

        # Convertir (x, y) en indices entiers pour accéder à la depth map
        points_int = np.round(points).astype(int)

        # Récupérer les valeurs de profondeur (z) à ces coordonnées
        z_values = depth_map[points_int[:, 1], points_int[:, 0]]

        # Assembler les coordonnées (x, y, z)
        points_with_depth = np.column_stack((points_int, z_values))

        return points_with_depth


    def fit_plane_from_4_points(self,points, depth_map_shape):
        """
        Ajuste un plan à partir de 4 points sélectionnés sur une depth map.
        Retourne une image du plan de même dimension que la depth map.
        
        :param points: np.array([[x1, y1, z1], [x2, y2, z2], [x3, y3, z3], [x4, y4, z4]])
        :param depth_map_shape: Tuple (hauteur, largeur) de la depth map
        :return: Matrice 2D représentant le plan ajusté
        """
        # Séparation des coordonnées
        Xp, Yp, Zp = points[:, 0], points[:, 1], points[:, 2]

        # Construction de la matrice du système linéaire
        A = np.column_stack((Xp, Yp, np.ones(4)))
        B = Zp  # Valeurs de profondeur (z)

        # Résolution du système Ax = B pour obtenir a, b et d (on suppose c = -1 pour normaliser)
        coeffs, _, _, _ = np.linalg.lstsq(A, B, rcond=None)
        a, b, d = coeffs
        c = -1  # Normalisation

        print(f"Plan estimé : {a:.3f}x + {b:.3f}y + {c:.3f}z = {d:.3f}")

        # Création des coordonnées (X, Y) pour la depth map complète
        h, w = depth_map_shape
        X, Y = np.meshgrid(np.arange(w), np.arange(h))

        # Calcul du plan ajusté pour toute l'image
        Z_fit = (d - a * X - b * Y) / c  # Résolution de l'équation du plan

        return Z_fit

    def reconstruction(self):

        ZOBJ_moy= self.get_z_from_raw(self.raw_measure)
        plan_points=self.select_4_points(ZOBJ_moy)
        plan_ref=self.fit_plane_from_4_points(plan_points,np.shape(ZOBJ_moy))
        hauteur=ZOBJ_moy-plan_ref
  
        return hauteur 
    
    def polynomial_smooth(self,depth_map):

        OBJ_lisse = np.zeros_like(depth_map) #matrice vide

        #boucle pour appliquer la modélisation polynomiale à chaque profil
        for i in range(depth_map.shape[1]):
            y = depth_map[:,i]
            x = np.arange(len(y))
            
            # Ajustement d'un polynôme de degré 
            coeffs = np.polyfit(x, y, deg=21)
            y_lisse = np.polyval(coeffs, x)
            OBJ_lisse[:, i] = y_lisse
        
        hauteur = OBJ_lisse*(-20000)+192 #hauteur en nm
        return hauteur
    

    def save_reconstructed_image(self,hauteur,save_path):
        depth_map_title="depthmap.npy"
        np.save(save_path+"\\"+depth_map_title,hauteur)




  