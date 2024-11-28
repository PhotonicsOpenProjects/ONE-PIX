import numpy as np
import os
import sys
import time

sys.path.append(f"..{os.sep}..{os.sep}")
from core.Acquisition import Acquisition
from core.Reconstruction import Reconstruction
from plugins.imaging_methods.FIS_common_functions.FIS_common_reconstruction import (
    FisCommonReconstruction as Fis,
)
import json
from datetime import date
from scipy.signal import savgol_filter


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
    json.dump(hardware_params, file, indent=4)


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
# Calculate the spatial reference (median to handle outliers + normalization)
spat_ref = np.median(raw_ref, axis=2)  # Use the spatial median to handle outliers

# Robust normalization using IQR
q1 = np.percentile(spat_ref, 25)  # 25th percentile
q3 = np.percentile(spat_ref, 75)  # 75th percentile
iqr = q3 - q1  # Interquartile range
spat_ref_normalized = (spat_ref - q1) / iqr  # Robust normalization
# Scale to [0, 1]
spat_ref_normalized = (spat_ref_normalized - np.min(spat_ref_normalized)) / (
    np.max(spat_ref_normalized) - np.min(spat_ref_normalized)
)
# Calculate the spectral reference (median + smoothing)
spec_ref = np.median(raw_ref, axis=(0, 1))  # Compute the spectral median
spec_ref-=np.median(spec_ref[:10])
#spec_ref = savgol_filter(spec_ref, window_length=7, polyorder=3)  # Optional: apply smoothing

"""
import matplotlib.pyplot as plt
plt.figure()
plt.imshow(spat_ref_normalized)
plt.show()

plt.figure()
plt.plot(spec_ref)
plt.show()
"""

# Build the normalized reference
ref = spat_ref_normalized[:, :, np.newaxis] * np.reshape(spec_ref, (1, 1, len(spec_ref)))

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
