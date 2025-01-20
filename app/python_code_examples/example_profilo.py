# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 15:07:02 2025

@author: luguen
"""

import os
import sys

sys.path.append(f"..{os.sep}..")
from core.ProfiloAcquisition import Profilo_Acquisition
from plugins.imaging_methods.Profilo.PatternsCreation import CreationPatterns
spatial_res=100
height=250
width=250
 
pc=CreationPatterns(spatial_res, height, width)
patterns=pc.creation_patterns()
profilo=Profilo_Acquisition(patterns,pc.pattern_order)
profilo.profilo_thread_acquisition()