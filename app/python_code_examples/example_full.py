import os
import sys

sys.path.append(f"..{os.sep}..")
from core.Acquisition import Acquisition
from core.Reconstruction import Reconstruction
from core.Analysis import Analysis

# Starting a new acquisition
acq = Acquisition()
acq.thread_acquisition()
acq.save_raw_data()

# Data reconstruction
rec = Reconstruction(acq)
rec.data_reconstruction()

filename = "test_datacube"
save_path = f".{os.sep}"
rec.save_reconstructed_image(filename, save_path)

# Analysis according to the acquisition method
ana = Analysis(rec)
ana.plot_rgb_image()
