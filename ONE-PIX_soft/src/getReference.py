"""
Created on Wed Jul 19 18:31:04 2023

@author: leo
"""


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
#print('/'.join(os.getcwd().split('/')[:-1]))
root_path = os.getcwd()
#sys.path.insert(0, root_path)

os.chdir(root_path)
# json_path = "./acquisition_param_ONEPIX.json"

from src.AcquisitionConfig import *

 




def define_params(test):
    # test.integration_time_ms=400
    test.OP_init()
    # print("test")
    f = open(jsonpath)
    acq_params = json.load(f)
    f.close()
    acq_params["integration_time_ms"] = test.integration_time_ms
    if test.integration_time_ms<12:
        test.periode_pattern=120
    else:
        test.periode_pattern = 10*test.integration_time_ms
    #acq_params["pattern_method"] = "FourierSplit"
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

 

# getting screen's width in pixels using tkinter
# test_win = Tk()
# screen_width = test_win.winfo_screenwidth()
# print(screen_width)
# test_win.destroy()

 

# create static pattern to be displayed
proj = tk.Tk()
proj.geometry("{}x{}+{}+{}".format(test.width, test.height, screenWidth, 0))
# proj.update()
y = list(range(test.height))  # horizontal vector for the pattern creation
x = list(range(test.width))  # vertical vector for the pattern creation
Y, X = np.meshgrid(x, y)  # horizontal and vertical array for the pattern creation
A = 2 * np.pi * X * 10 / test.height
B = 2 * np.pi * Y * 10 / test.width
pos_r = np.cos(A + B)  # gray pattern creation
pos_r[pos_r < 0] = 0

pil_img = PIL.Image.fromarray(255 * pos_r)

img = PIL.ImageTk.PhotoImage(master=proj, image=pil_img)
label_test_proj = tk.Label(proj, image=img)
label_test_proj.image = img
label_test_proj.pack()

# test.r
proj.update()


 

define_params(test)
proj.destroy()

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


# if not('spectral_ref' in os.listdir()):
#     os.mkdir('reference')
    
# if ('/'.join(os.path.abspath(os.curdir).split('\\'))).split('/')[-1]

