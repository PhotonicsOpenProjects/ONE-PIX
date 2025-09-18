from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
import numpy as np 

# acq = Acquisition(imaging_method_name="FourierSplit")
# #acq = Acquisition()
# acq.thread_acquisition()
# acq.save_raw_data()
# print(list(acq.acquisition_results.keys()))
rec=Reconstruction()
rec.data_reconstruction()
hypercube=rec.imaging_method.reconstructed_image





