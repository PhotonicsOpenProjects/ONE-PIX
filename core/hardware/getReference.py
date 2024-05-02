import numpy as np
import os
import sys
import glob
import time

sys.path.append(f"..{os.sep}..{os.sep}")
from core.Acquisition import Acquisition
from core.Reconstruction import Reconstruction
from plugins.imaging_methods.FIS_common_functions.FIS_common_reconstruction import (
    FisCommonReconstruction as Fis,
)
import json
from datetime import date
import shutil


# Normalisation datacube parameters setting
acquisition_json_path = f"..{os.sep}..{os.sep}conf{os.sep}acquisition_parameters.json"
hardware_json_path = f"..{os.sep}..{os.sep}conf{os.sep}hardware_config.json"
software_json_path = f"..{os.sep}..{os.sep}conf{os.sep}software_config.json"

with open(acquisition_json_path) as f:
    acq_params = json.load(f)

with open(software_json_path) as f:
    soft_params = json.load(f)

soft_params["normalisation_path"] = ""
acq_params["spatial_res"] = 21
acq_params["imaging_method"] = "FourierSplit"

with open(acquisition_json_path, "w") as file:
    json.dump(acq_params, file, indent=4)

with open(software_json_path, "w") as file:
    json.dump(soft_params, file, indent=4)


test = Acquisition()
test.hardware.spectrometer.spec_open()
test.hardware.projection.get_integration_time_auto(test)
# save auto measured integration time
with open(hardware_json_path) as f:
    hardware_params = json.load(f)

hardware_params["integration_time_ms"] = test.hardware.spectrometer.integration_time_ms

with open(hardware_json_path, "w") as file:
    json.dump(acq_params, file, indent=4)


if not "References" in os.listdir(f"..{os.sep}..{os.sep}app"):
    os.mkdir(f"..{os.sep}..{os.sep}app{os.sep}References")
# os.chdir('Hypercubes')
fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
actual_time = time.strftime("%H-%M-%S")  # get the current time
# folder_name = f"Normalisation_{fdate}_{actual_time}"
# os.mkdir(f"..{os.sep}..{os.sep}app{os.sep}References{os.sep}{folder_name}")
# os.chdir(folder_name)
# os.mkdir(f"..{os.sep}..{os.sep}app{os.sep}References{os.sep}{folder_name}{os.sep}reference")

save_path = f"..{os.sep}..{os.sep}app{os.sep}References{os.sep}"
test.thread_acquisition(path=save_path, time_warning=False)

# load hypercube
rec = Reconstruction(test)
rec.data_reconstruction()
raw_ref = rec.imaging_method.reconstructed_image
# normalised reference hypercube supposing vigneting is non spectrally dependant
spat_ref = np.mean(raw_ref, 2)
spat_ref = (spat_ref) / (np.max(spat_ref) - np.min(spat_ref))
spec_ref = np.mean(raw_ref, (0, 1))

ref = spat_ref[:, :, np.newaxis] * np.reshape(spec_ref, (1, 1, np.size(spec_ref)))
header = rec.create_reconstruction_header()
saver = Fis()
saver.save_acquisition_envi(
    ref,
    test.hardware.spectrometer.wavelengths,
    header,
    f"reference_{fdate}_{actual_time}",
    save_path,
)
save_path = save_path + os.sep + f"reference_{fdate}_{actual_time}"
# Notify in json file where to find the normalised datacube
with open(software_json_path) as f:
    software_params = json.load(f)

acq_params["normalisation_path"] = os.path.abspath(save_path)
with open(software_json_path, "w") as file:
    json.dump(software_params, file)

# shutil.copy(glob.glob(save_path+os.sep+'ONE-PIX*'+os.sep+'*.txt')[0],os.path.abspath(save_path+os.sep+'reference'))
