from onepix.Acquisition import Acquisition

acq = Acquisition(imaging_method_name="has")
print(acq.imaging_method_name)
acq.init_measure() 
acq.thread_acquisition()
acq.save_raw_data()
