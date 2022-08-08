import numpy as np
import matplotlib.pyplot as plt

spectre=np.load("/home/pi/Desktop/ONE-PIX/ONE-PIX_soft/Hypercubes/ONE-PIX_acquisition_08_08_2022_09-37-52/spectra_08_08_2022_09-37-52.npy")

plt.figure()
plt.plot(spectre.T)
plt.show()


