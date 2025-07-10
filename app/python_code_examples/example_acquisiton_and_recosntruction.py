from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
import numpy as np 

acq = Acquisition(imaging_method_name="FourierSplit")
acq.thread_acquisition()
rec=Reconstruction(acq)
rec.data_reconstruction()
hypercube=rec.imaging_method.reconstructed_image
print(np.shape(hypercube))



