import os
import sys

sys.path.append(f"..{os.sep}..")
from core.Acquisition import Acquisition




acq = Acquisition(imaging_method_name="HadamardSplit",spatial_res=16)
#acq = Acquisition(imaging_method_name='HadamardWalshSplit')
acq.update_hardware(integration_time_ms=3)
acq.thread_acquisition(time_warning=False)
acq.save_raw_data()

acq = Acquisition(imaging_method_name='HadamardSplit',spatial_res=8)
acq.update_hardware(integration_time_ms=1)
acq.thread_acquisition(time_warning=False)
acq.save_raw_data()