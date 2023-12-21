
import os 
import sys
sys.path.append(f'..{os.sep}..')
from core import Acquisition

acq=Acquisition.Acquisition()
acq.init_measure()
acq.thread_acquisition()
acq.save_raw_data()