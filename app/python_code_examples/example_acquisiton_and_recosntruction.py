from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
import numpy as np 
import matplotlib.pyplot as plt 
# acq = Acquisition(imaging_method_name="FourierSplit")
# acq.thread_acquisition()
# acq.save_raw_data()
# print(list(acq.acquisition_results.keys()))
rec=Reconstruction(plot_result=True)
rec.data_reconstruction()

plt.figure()
plt.imshow(rec.reconstruction_results["result2plot"])
plt.show()



