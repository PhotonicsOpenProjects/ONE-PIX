import sys
import os 
actual_path=os.getcwd()
os.chdir("..")
os.chdir("..")
root_path=os.getcwd()
os.chdir(actual_path)

sys.path.insert(0, root_path)
from core import Acquisition
acq=Acquisition.Acquisition()
acq.thread_acquisition()
acq.save_raw_data()