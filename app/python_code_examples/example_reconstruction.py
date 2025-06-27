import os
from onepix.Reconstruction import Reconstruction

rec = Reconstruction()
rec.data_reconstruction()

filename = "test_datacube"
save_path = f".{os.sep}"
rec.save_reconstructed_image(filename, save_path)
