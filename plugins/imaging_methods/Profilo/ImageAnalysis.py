import os
import sys
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
import matplotlib.pyplot as plt 
import numpy as np

class Analysis:


    def __init__(self,data_path=None):
        self.data_path = data_path



    def plot_reconstructed_image(self,hauteur):
        fig = plt.figure(13)
        ax = fig.add_subplot(111, projection='3d')


        X = np.arange(hauteur.shape[1])
        Y = np.arange(hauteur.shape[0])
        X, Y = np.meshgrid(X, Y)

        surf = ax.plot_surface(X, Y,hauteur , cmap='viridis')
        ax.view_init(20, 70)
        # ax.set_xlim(0, 2900)
        fig.colorbar(surf)

        plt.show()
        
        plt.figure(14)
        plt.plot(hauteur[1900, :])
        plt.grid()
        plt.show()