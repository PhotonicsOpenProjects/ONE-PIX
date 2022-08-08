import numpy as np
import matplotlib.pyplot as plt

spectre=np.load("/home/pi/Desktop/ONE-PIX/ONE-PIX_soft/Hypercubes/ONE-PIX_acquisition_08_08_2022_10-19-54/spectra_08_08_2022_10-19-54.npy")

plt.figure()
plt.plot(spectre.T)
plt.show()


