from onepix.Acquisition import Acquisition

acq = Acquisition(imaging_method_name="HadamardSplit")
acq.thread_acquisition()
acq.save_raw_data()

