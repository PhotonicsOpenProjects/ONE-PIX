import os
from onepix.Reconstruction import Reconstruction
import numpy as np 
rec = Reconstruction()
print(np.shape(rec.acquisition_dict["patterns"]))

#rec.load_acquisition_results()
#rec.data_reconstruction()

# filename = "test_datacube"
# save_path = f".{os.sep}"
# rec.save_reconstructed_image(filename, save_path)
