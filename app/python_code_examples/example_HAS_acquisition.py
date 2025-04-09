import os
import sys

sys.path.append(f"..{os.sep}..")
from core.Acquisition import Acquisition

acq = Acquisition(imaging_method_name="Addressing")
print(acq.imaging_method_name)
acq.thread_acquisition()
acq.save_raw_data()
