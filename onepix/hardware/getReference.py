import json
import time
from datetime import date
from pathlib import Path

import numpy as np

from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from fis_common_function.FIS_common_reconstruction import (
    FisCommonReconstruction as Fis,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONF_DIR = REPO_ROOT / "conf"

acquisition_json_path = CONF_DIR / "acquisition_parameters.json"
hardware_json_path = CONF_DIR / "hardware_config.json"
software_json_path = CONF_DIR / "software_config.json"


def main():
    # Normalisation datacube parameters setting
    with open(acquisition_json_path) as f:
        acq_params = json.load(f)

    with open(software_json_path) as f:
        soft_params = json.load(f)

    soft_params["normalisation_path"] = ""
    acq_params["spatial_res"] = 21
    acq_params["imaging_method_name"] = "FourierSplit"

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

    references_dir = REPO_ROOT / "app" / "References"
    references_dir.mkdir(parents=True, exist_ok=True)

    fdate = date.today().strftime("%d_%m_%Y")  # convert the current date in string
    actual_time = time.strftime("%H-%M-%S")  # get the current time
    save_path = str(references_dir)

    test.thread_acquisition()

    # load hypercube
    rec = Reconstruction(test.acquisition_results)
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

    # Build the normalized reference
    ref = spat_ref_normalized[:, :, np.newaxis] * np.reshape(spec_ref, (1, 1, len(spec_ref)))

    header = rec.create_reconstruction_header()
    saver = Fis()
    reconstruction_results = {
        "reconstructed_data": ref,
        "wavelengths": test.hardware.spectrometer.wavelengths,
    }
    saver.save_acquisition_envi(
        reconstruction_results,
        header,
        save_envi_name=f"reference_{fdate}_{actual_time}",
        save_path=save_path,
    )

    soft_params["normalisation_path"] = str(
        references_dir / f"reference_{fdate}_{actual_time}"
    )

    with open(software_json_path, "w") as file:
        json.dump(soft_params, file)


if __name__ == "__main__":
    main()
