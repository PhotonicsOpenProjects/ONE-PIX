# -*- coding: utf-8 -*-
"""
Created on Fri Oct  8 17:09:58 2021
@author: mribes & grussias
"""
from src.AcquisitionConfig import *
begin_script=time.time()

"""
ONEPIX data initialisation
"""
json_path="./acquisition_param_ONEPIX.json"
acquisition_config = OPConfig(json_path)
OP_init(acquisition_config)
print(f"Estimated acquisition duration : {acquisition_config.pattern_lib.nb_patterns*acquisition_config.periode_pattern/(60*1000)} min ")
"""
Start ONEPIX acquisition  
"""
print("Start acquisition")
acquisition_config=thread_acquisition(acquisition_config)
duree_script=time.time()-begin_script
print(f"ONEPIX acquisition completed in {duree_script/60} min")

