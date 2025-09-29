from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
import numpy as np 
import matplotlib.pyplot as plt 


# acq = Acquisition(imaging_method_name="Spyrit")
# acq.thread_acquisition()
# acq.save_raw_data()

rec=Reconstruction(plot_result=True)
rec.data_reconstruction()
print(list(rec.reconstruction_results.keys()))
plt.figure()
plt.imshow(rec.reconstruction_results["result2plot"])
plt.show()
rec.save_reconstructed_image()




