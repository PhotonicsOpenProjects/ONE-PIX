from onepix.Acquisition import Acquisition

acq = Acquisition(imaging_method_name="spod")
acq.init_measure()      
acq.thread_acquisition()
acq.save_raw_data()
