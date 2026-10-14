from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
import numpy as np 
import matplotlib.pyplot as plt 


acq = Acquisition(imaging_method_name="fouriersplit")
acq.thread_acquisition()
acq.save_raw_data()

rec=Reconstruction( acquisition=acq.acquisition_results,plot_result=True)
rec.data_reconstruction()
print(list(rec.reconstruction_results.keys()))
print(rec.reconstruction_results.keys())
print(rec.reconstruction_results["metadata"]["imaging_method_name"])

plt.figure()
plt.imshow(rec.reconstruction_results["result2plot"])
plt.show()
#rec.save_reconstruction_results(filename="test_datacube", save_path=".")




