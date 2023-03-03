
from src.AcquisitionConfig import *
begin_script=time.time()

"""
ONE-PIX data initialisation
"""
json_path="./acquisition_param_ONEPIX.json"
acquisition_config = OPConfig(json_path)
acquisition_config.OP_init()
print(f"Estimated acquisition duration : {round(1.5*acquisition_config.pattern_lib.nb_patterns*acquisition_config.periode_pattern/(60*1000),2)} min ")

"""
Start ONE-PIX acquisition  
"""
print("Start acquisition")
acquisition_config.thread_acquisition()
duree_script=time.time()-begin_script
print(f"ONE-PIX acquisition completed in {duree_script/60} min")

