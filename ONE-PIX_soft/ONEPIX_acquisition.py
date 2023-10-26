"""
ONEPIX_acquisition allows to launch ONE-PIX measures according to the json parameters file.
"""

from src.AcquisitionConfig import *
begin_script=time.time()

"""
ONE-PIX data initialisation
"""
json_path="./acquisition_param_ONEPIX.json"
print(json_path)
config = OPConfig(json_path)

# Automatic integration time setting comment to keep json's file value
config.OP_init() 
est_dur=round(1.5*config.pattern_lib.nb_patterns*config.periode_pattern/(60*1000),2)
print(f"Estimated acquisition duration : {est_dur} min ")

"""
Start ONE-PIX acquisition  
"""
print("Start acquisition")
config.thread_acquisition()
duration=time.time()-begin_script
print(f"ONE-PIX acquisition completed in {duration/60} min")
