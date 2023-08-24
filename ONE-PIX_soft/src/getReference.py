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
import json
from datetime import date
import screeninfo

root_path = os.getcwd()
os.chdir(root_path)

def define_params(test):
    test.OP_init()
    f = open(jsonpath)
    acq_params = json.load(f)
    f.close()
    acq_params["integration_time_ms"] = test.integration_time_ms
    print(test.integration_time_ms)
    file = open(jsonpath, "w")
    json.dump(acq_params, file)
    file.close()

jsonpath = '/'.join([root_path,'../acquisition_param_ONEPIX.json'])
f = open(jsonpath)
acq_params = json.load(f)
f.close()
acq_params["spatial_res"] = 5
acq_params["pattern_method"] = "FourierSplit"
file = open(jsonpath, "w")
json.dump(acq_params, file)
file.close()

test = OPConfig(jsonpath)
define_params(test)

if not "Hypercubes" in os.listdir("../"):
    os.mkdir("../Hypercubes")
#os.chdir('Hypercubes')
fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
actual_time = time.strftime("%H-%M-%S")  # get the current time
folder_name = f"{fdate}_{actual_time}"
os.mkdir(f"../Hypercubes/{folder_name}")
#os.chdir(folder_name)
os.mkdir(f"../Hypercubes/{folder_name}/reference")

f = open(jsonpath)
acq_params = json.load(f)
f.close()
acq_params["data_path"] = ('/'.join(os.path.abspath(f"../Hypercubes/{folder_name}/reference").split('\\')))
file = open(jsonpath, "w")
json.dump(acq_params, file)
file.close()

test.thread_acquisition(path = f"../Hypercubes/{folder_name}/reference", time_warning = False)