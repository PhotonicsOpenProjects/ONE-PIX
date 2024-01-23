from scipy.linalg import hadamard
import numpy as np 
import matplotlib.pyplot as plt 
dim=4
hadamard_matrix=hadamard(dim**2,dtype=np.int8)

plt.figure()
plt.imshow(hadamard_matrix,cmap='gray')
plt.show()