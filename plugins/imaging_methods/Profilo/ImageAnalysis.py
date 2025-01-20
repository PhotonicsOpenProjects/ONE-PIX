import os
import sys
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
import matplotlib.pyplot as plt 
import numpy as np

class Analysis:


    def __init__(self,data_path=None):
        self.data_path = data_path



    def plot_reconstructed_image(self,depth_map):
        fig = plt.figure(13)
        ax = fig.add_subplot(111, projection='3d')


        X = np.arange(depth_map.shape[1])
        Y = np.arange(depth_map.shape[0])
        X, Y = np.meshgrid(X, Y)

        # phase_lisse2=phase_lisse*(-1034)+3277
        OBJ_conv=depth_map*(-1016)+3200
        surf = ax.plot_surface(X, Y, depth_map , cmap='viridis')
        ax.view_init(20, 70)
        # ax.set_xlim(0, 2900)
        fig.colorbar(surf)


        plt.show()