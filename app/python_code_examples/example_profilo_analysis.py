import numpy as np
import matplotlib.pyplot as plt
from plugins.imaging_methods.Profilo.ImageReconstruction import ProfiloReconstruction
from plugins.imaging_methods.Profilo.ImageAnalysis import Analysis
from onepix.hardware.coregistration_lib import *


rec=ProfiloReconstruction("put path of the raw measure of the sample here")
rec.load_reference("put path of the raw measure of the reference here")

depth_map_mes_ref_norm=rec.reconstruction_with_ref()
depth_map_plan_ref=rec.reconstruction()



an=Analysis()
an.plot_reconstructed_image(depth_map_plan_ref)
an.plot_reconstructed_image(depth_map_mes_ref_norm)
