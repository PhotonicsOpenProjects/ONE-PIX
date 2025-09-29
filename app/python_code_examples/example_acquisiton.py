from onepix.Acquisition import Acquisition

acq = Acquisition(imaging_method_name="Addressing")
acq.thread_acquisition()
acq.save_raw_data()

