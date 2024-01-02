import numpy as np
import matplotlib.pyplot as plt
import os
import customtkinter as ctk
import tkinter as tk
import PIL
import time
from functools import partial
import sys
sys.path.insert(0, os.path.abspath('../'))
from src.AcquisitionConfig import *
from src.DatacubeReconstructions import *
import json
from datetime import date
import screeninfo
import shutil


# Normalisation datacube parameters setting
jsonpath = '../acquisition_param_ONEPIX.json'  
with open(jsonpath) as f:
    acq_params = json.load(f)

acq_params["normalisation_path"] =""
acq_params["spatial_res"] = 21
acq_params["pattern_method"] = "FourierSplit"

with open(jsonpath, "w") as file:
    json.dump(acq_params, file,indent=4)


test = OPConfig(jsonpath)
test.OP_init()
#save auto measured integration time
f = open(jsonpath)
acq_params = json.load(f)
f.close()
acq_params["integration_time_ms"] = test.integration_time_ms
with open(jsonpath, "w") as file:
    json.dump(acq_params, file,indent=4)



if not "Hypercubes" in os.listdir("../"):
    os.mkdir("../Hypercubes")
#os.chdir('Hypercubes')
fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
actual_time = time.strftime("%H-%M-%S")  # get the current time
folder_name = f"Normalisation_{fdate}_{actual_time}"
os.mkdir(f"../Hypercubes/{folder_name}")
#os.chdir(folder_name)
os.mkdir(f"../Hypercubes/{folder_name}/reference")

save_path=f"../Hypercubes/{folder_name}"
test.thread_acquisition(path =save_path , time_warning = False)

# load hypercube
raw_ref=load_hypercube(opt=save_path+'/'+'ONE-PIX*')["hyperspectral_image"]

# normalised reference hypercube supposing vigneting is non spectrally dependant
spat_ref=np.mean(raw_ref,2)
spat_ref=(spat_ref)/(np.max(spat_ref)-np.min(spat_ref))
spec_ref=np.mean(raw_ref,(0,1))

ref=spat_ref[:,:,np.newaxis]*np.reshape(spec_ref,(1,1,np.size(spec_ref)))

py2envi(f"reference_{fdate}_{actual_time}",ref,test.wavelengths,save_path+'/reference')

# Notify in json file where to find the normalised datacube
with open(jsonpath) as f:
    acq_params = json.load(f)

acq_params["normalisation_path"] = os.path.abspath(save_path+'/reference')
with open(jsonpath, "w") as file:
    json.dump(acq_params, file)

shutil.copy(glob.glob(save_path+'/'+'ONE-PIX*'+'/*.txt')[0],os.path.abspath(save_path+'/reference'))
