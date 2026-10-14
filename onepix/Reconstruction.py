import numpy as np
import os
import time
from datetime import date
from pathlib import Path

from tkinter import *
from tkinter.filedialog import askdirectory

from onepix.ImagingMethodBridge import *
from onepix import utils as utils

import logging
from onepix.logging_config import root

logger = logging.getLogger(__name__)


# ==========================================================
# HEADER UTILS
# ==========================================================
def get_header_data(path):

    header = []

    with open(path, "r") as file:

        for line in file.readlines():

            header.append(
                line.split(":")
            )

    acq_data = dict()

    acq_data["acquisition_name"] = (
        header[0][0][8:]
    )

    for x in header:

        if x[0].strip() == "Imaging method":

            acq_data["imaging_method_name"] = (
                x[1].strip()
            )

        if x[0].strip() == "Integration time":

            acq_data["integration_time_ms"] = (
                float(x[1].strip()[:-2])
            )

    logging.info(
        "header data is loaded"
    )

    return acq_data


# ==========================================================
# RECONSTRUCTION
# ==========================================================
class Reconstruction:
    """
    Class OPReconstruction to reconstruct
    datacubes according to a ONE-PIX method
    """

    def __init__(
        self,
        acquisition=None,
        plot_result=False
    ):

        self.plot_result = plot_result

        self.reconstruction_results = {}

        # ==================================================
        # ACQUISITION INPUT
        # ==================================================
        #
        # acquisition can be:
        #
        # - None
        #       -> GUI picker
        #
        # - dict
        #       -> already loaded acquisition dict
        #
        # - str / Path
        #       -> acquisition JSON path
        #
        # ==================================================

        # --------------------------------------------------
        # GUI PICKER
        # --------------------------------------------------
        if acquisition is None:

            self.acquisition_dict = (
                self.load_acquisition_results()
            )

        # --------------------------------------------------
        # DICT INPUT
        # --------------------------------------------------
        elif isinstance(acquisition, dict):

            self.acquisition_dict = acquisition

        # --------------------------------------------------
        # JSON PATH INPUT
        # --------------------------------------------------
        elif isinstance(acquisition, (str, Path)):

            self.acquisition_dict = (
                utils.load_dict_json(
                    acquisition
                )
            )

        # --------------------------------------------------
        # INVALID INPUT
        # --------------------------------------------------
        else:

            raise TypeError(
                "acquisition must be:\n"
                "- None\n"
                "- dict\n"
                "- str\n"
                "- Path"
            )

        # ==================================================
        # ACQUISITION DATA
        # ==================================================
        self.imaging_method_name = (
            self.acquisition_dict[
                "imaging_method_name"
            ]
        )

        self.spectra = (
            self.acquisition_dict[
                "spectra"
            ]
        )

        self.pattern_order = (
            self.acquisition_dict[
                "patterns_order"
            ]
        )

        self.wavelengths = (
            self.acquisition_dict[
                "wavelengths"
            ]
        )

        # ==================================================
        # INIT
        # ==================================================
        self.spatial_res = 0

        self.height = 0

        self.width = 0

        self.imaging_method = (
            ImagingMethodBridge(
                self.imaging_method_name,
                self.height,
                self.width,
                plot_result=self.plot_result
            )
        )

        logging.info(
            f"{self.imaging_method_name} "
            f"Reconstruction class is init"
        )

    # ======================================================
    # GUI LOAD ACQUISITION RESULTS
    # ======================================================
    def load_acquisition_results(self):

        """
        Open GUI picker and load
        acquisition_results_*.json
        """

        script_path = os.path.abspath(__file__)

        script_dir = os.path.dirname(
            script_path
        )

        parent_dir = os.path.dirname(
            script_dir
        )

        measure_dir = os.path.join(
            parent_dir,
            "measure"
        )

        root = Tk()

        root.withdraw()

        root.attributes("-topmost", 1)

        folder_path = askdirectory(
            title=(
                "Select the folder "
                "containing the acquisitions"
            ),
            initialdir=measure_dir,
        )

        for fname in os.listdir(folder_path):

            if (
                fname.startswith(
                    "acquisition_results_"
                )
                and fname.endswith(".json")
            ):

                fpath = os.path.join(
                    folder_path,
                    fname
                )

                logging.info(
                    f"Loading acquisition : "
                    f"{fpath}"
                )

                return utils.load_dict_json(
                    fpath
                )

        raise FileNotFoundError(
            "⚠️ No acquisition_results_*.json "
            "found in this folder"
        )

    # ======================================================
    # NAN CORRECTION
    # ======================================================
    def nan_corr(self):

        try:

            idx_nan = np.argwhere(
                np.isnan(self.spectra)
            )[0, :-1]

            self.spectra[idx_nan, :] = (
                self.spectra[idx_nan - 1, :]
            )

        except IndexError:

            pass

    # ======================================================
    # DATA RECONSTRUCTION
    # ======================================================
    def data_reconstruction(self):

        self.imaging_method.reconstruction(
            self.acquisition_dict,
            plot_result=self.plot_result
        )

        # Carry the acquisition's metadata forward (imaging method name,
        # hardware settings, timing - see Acquisition.build_metadata())
        # so the saved reconstruction stays traceable back to how the
        # measurement it's built from was taken, regardless of which
        # imaging-method plugin produced reconstruction_results.
        # setdefault() backfills imaging_method_name for an
        # acquisition_dict that predates this field (e.g. an older raw
        # acquisition save, or metadata missing for some other reason).
        # Placed first so it's the first thing visible when the saved
        # JSON is opened, ahead of the (potentially large) datacube.
        metadata = dict(
            self.acquisition_dict.get("metadata", {})
        )
        metadata.setdefault(
            "imaging_method_name", self.imaging_method_name
        )

        # imaging_method_name is NOT repeated at the top level here - it
        # lives only in metadata. The "Specific Analysis" GUI (external
        # onepix-fis-common-function package) needs it at the top level
        # with no metadata fallback, but that's handled by adapting the
        # result at the one point it's handed to that package
        # (app/GUI/flask/blueprints/analysis/routes.py's
        # _result_for_specific_analysis()) instead of storing a
        # duplicate copy in every saved file.
        self.reconstruction_results = (
            {"metadata": metadata}
            | self.imaging_method.reconstruction_results
        )

        logging.info(
            "raw datas are reconstructed now"
        )

        if self.plot_result:

            logging.info(
                "plot result is created"
            )

    # ======================================================
    # CREATE PLOT
    # ======================================================
    def create_plot_result(self):

        self.imaging_method.create_plot_result()


# ======================================================
# SAVE RECONSTRUCTION RESULTS
# ======================================================
    def save_reconstruction_results(
        self,
        filename=None,
        save_path=None
    ):

        # ==================================================
        # DEFAULT SAVE PATH
        # ==================================================
        if save_path is None:

            save_path = (
                Path(__file__)
                .resolve()
                .parent.parent
                / "measure"
            )

        save_path = Path(save_path)

        save_path.mkdir(exist_ok=True)

        # ==================================================
        # DATE
        # ==================================================
        fdate = date.today().strftime(
            "%d_%m_%Y"
        )

        actual_time = time.strftime(
            "%H-%M-%S"
        )

        # ==================================================
        # DEFAULT FILENAME
        # ==================================================
        if filename is None:

            filename = (
                f"reconstruction_results_"
                f"{fdate}_{actual_time}.json"
            )

        filepath = save_path / filename

        # ==================================================
        # GENERIC JSON SAVE
        # ==================================================
        utils.save_dict_json(
            self.reconstruction_results,
            filepath
        )

        # ==================================================
        # LOGS
        # ==================================================
        size_mb = (
            os.path.getsize(filepath)
            / (1024**2)
        )

        logger.info(
            f"Saved reconstruction : "
            f"{filepath}"
        )

        logger.info(
            f"File size : "
            f"{size_mb:.2f} MB"
        )

    # ======================================================
    # HEADER
    # ======================================================
    def create_reconstruction_header(self):

        fdate = date.today().strftime(
            "%d_%m_%Y"
        )

        actual_time = time.strftime(
            "%H-%M-%S"
        )

        if type(self.acquisition_dict) is dict:

            header = (
                f"ONE-PIX_reconstructed_"
                f"acquisition_"
                f"{fdate}_{actual_time}"
                + "\n"
                + "-----------------------------"
                + "-------------------"
                + "\n\n"
                + f"Imaging method: "
                f"{self.imaging_method_name}"
                + "\n"
            )

        else:

            self.acquisition_dict.create_acquisition_header()

            header = (
                self.acquisition_dict.header
            )

        return header