from core.acquisition import  *
from core.reconstruction import *
from core.analysis import *

acq=Acquisition()
acq.thread_acquisition()

rec=Reconstruction(acq)
rec.reconstruct()
rec.save()

ana=Analysis(rec)
ana.plot_false_rgb()