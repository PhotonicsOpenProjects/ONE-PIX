from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from onepix.Analysis import Analysis

# Starting a new acquisition
acq = Acquisition()
acq.thread_acquisition()
acq.save_raw_data()

# Data reconstruction
rec = Reconstruction(acquisition=acq.acquisition_results, plot_result=True)
rec.data_reconstruction()

rec.save_reconstruction_results(filename="test_datacube", save_path=".")

# Analysis according to the acquisition method
ana = Analysis(reconstruction_dict=rec.reconstruction_results, plot_result=True)
ana.data_analysis(pipeline_steps=[("snv", {})])
ana.save_analysis_results(filename="test_analysis", save_path=".")
