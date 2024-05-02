import os
import sys

sys.path.append(f"..{os.sep}..")
from core.Acquisition import Acquisition

acq = Acquisition()
acq.thread_acquisition()
acq.save_raw_data()
