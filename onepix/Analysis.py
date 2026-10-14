import os
import time
import logging

import numpy as np

from datetime import date, datetime
from pathlib import Path

from tkinter import *
from tkinter.filedialog import askdirectory

from spectra_core.pipeline import Pipeline

from spectra_core.plugins.discovery import (
    discover_transforms,
    discover_analyses
)

from onepix.ImagingMethodBridge import *
from onepix import utils as utils
from onepix.logging_config import root


logger = logging.getLogger(__name__)


def tabulate_outputs(outputs):
    """Analysis steps' outputs - one {name: value} dict per spectrum,
    as spectra_core's Pipeline returns them - as a table:
    {"names": [...], "values": (n spectra, n names) float array}, NaN
    where a spectrum has no value. Only scalar numeric outputs are kept.
    None if there are none."""

    names = []

    for row in outputs:
        for name, value in row.items():
            if name not in names and np.ndim(value) == 0:
                try:
                    float(value)
                except (TypeError, ValueError):
                    continue
                names.append(name)

    if not names:
        return None

    values = np.full((len(outputs), len(names)), np.nan)

    for i, row in enumerate(outputs):
        for j, name in enumerate(names):
            try:
                values[i, j] = float(row[name])
            except (KeyError, TypeError, ValueError):
                pass

    return {"names": names, "values": values}


class Analysis:
    """
    Generic ONE-PIX analysis class.
    """

    def __init__(
        self,
        reconstruction_dict=None,
        plot_result=False
    ):

        self.plot_result = plot_result
        self.analysis_results = {}

        discover_transforms()
        discover_analyses()

        if reconstruction_dict is None:

            self.reconstruction_dict = (
                self.load_reconstruction_results()
            )

        elif isinstance(reconstruction_dict, dict):

            self.reconstruction_dict = reconstruction_dict

        elif isinstance(reconstruction_dict, (str, Path)):

            self.reconstruction_dict = (
                utils.load_dict_json(
                    reconstruction_dict
                )
            )

        else:

            raise TypeError(
                "reconstruction_dict must be None, dict, str or Path"
            )

        # imaging_method_name lives inside metadata on a current
        # reconstruction/analysis file; the top-level fallback keeps this
        # working on an older file saved before that (or a raw
        # acquisition-shaped dict, which still carries it at top level).
        self.imaging_method_name = (
            self.reconstruction_dict.get("imaging_method_name")
            or self.reconstruction_dict.get("metadata", {}).get("imaging_method_name")
        )

        if self.imaging_method_name is None:
            raise KeyError(
                "imaging_method_name not found (checked top level and "
                "metadata) in the given reconstruction_dict"
            )

        self.imaging_method = (
            ImagingMethodBridge(
                self.imaging_method_name,
                0,
                0,
                plot_result=self.plot_result
            )
        )

        logger.info(
            f"{self.imaging_method_name} "
            f"Analysis class is init"
        )

    # =====================================================
    # LOAD RECONSTRUCTION RESULTS
    # =====================================================

    def load_reconstruction_results(self):

        measure_dir = (
            Path(__file__)
            .resolve()
            .parent.parent
            / "measure"
        )

        root = Tk()
        root.withdraw()
        root.attributes("-topmost", 1)

        folder_path = askdirectory(
            title=(
                "Select the folder containing "
                "the reconstructed data"
            ),
            initialdir=measure_dir,
        )

        folder_path = Path(folder_path)

        for filepath in folder_path.glob("*.json"):

            if filepath.name.startswith(
                "reconstruction_results_"
            ) or filepath.name.startswith(
                "analysis_results_"
            ):

                logger.info(
                    f"Loading reconstruction/analysis : "
                    f"{filepath}"
                )

                return utils.load_dict_json(
                    filepath
                )

        raise FileNotFoundError(
            "⚠️ No reconstruction_results_*.json "
            "or analysis_results_*.json found in this folder"
        )

    # =====================================================
    # ANALYSIS
    # =====================================================
    def data_analysis(
        self,
        pipeline_steps
    ):

        pipeline = Pipeline(
            pipeline_steps
        )

        spectral_data = (
            self.imaging_method
            .result2spectraldata(
                self.reconstruction_dict
            )
        )

        spectral_result = pipeline.run(
            spectral_data
        )

        new_result = (
            self.imaging_method
            .spectraldata2result(
                spectral_result,
                self.reconstruction_dict
            )
        )

        # =====================================================
        # Clone du dict d'entrée puis écrasement/ajout des
        # résultats de l'analyse
        # =====================================================

        self.analysis_results = (
            self.reconstruction_dict.copy()
        )

        if new_result is not None:

            self.analysis_results.update(
                new_result
            )

        # =====================================================
        # Analysis steps' outputs, in one place whatever the imaging
        # method: each method stores them its own way (FIS as 2D
        # maps, HAS as a list of dicts...), this table is what the
        # GUI shows. Dropped when this run has no analysis step, so a
        # previous run's values never outlive the data they came from.
        # =====================================================

        self.analysis_results.pop("analysis_outputs", None)

        if isinstance(spectral_result, list):

            outputs = tabulate_outputs(spectral_result)

            if outputs is not None:

                self.analysis_results["analysis_outputs"] = outputs

        try:

            result2plot = (
                self.imaging_method
                .create_result2plot(
                    self.analysis_results
                )
            )

            if result2plot is not None:

                self.analysis_results[
                    "result2plot"
                ] = result2plot

        except Exception as e:

            logger.warning(
                f"Unable to create "
                f"result2plot : {e}"
            )

        # =====================================================
        # Track this analysis run for traceability/reuse. Appended (not
        # overwritten) so a chain of analysis runs on top of the same
        # reconstruction - e.g. loading a previously saved analysis and
        # applying further steps - keeps the full history of what was
        # applied, not just the last step. The acquisition/reconstruction
        # metadata this analysis was run on (if any - see
        # Acquisition.build_metadata() / Reconstruction.data_reconstruction())
        # is preserved alongside it. setdefault() backfills
        # imaging_method_name in metadata in case it's missing there for
        # some reason.
        # =====================================================

        metadata = dict(
            self.analysis_results.get("metadata", {})
        )

        metadata.setdefault(
            "imaging_method_name", self.imaging_method_name
        )

        analysis_history = list(
            metadata.get("analysis_history", [])
        )

        analysis_history.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "steps": pipeline_steps,
        })

        metadata["analysis_history"] = analysis_history

        self.analysis_results["metadata"] = metadata

        # imaging_method_name is NOT repeated at the top level here - see
        # the matching comment in Reconstruction.data_reconstruction().

    # =====================================================
    # SAVE ANALYSIS RESULTS
    # =====================================================

    def save_analysis_results(
        self,
        filename=None,
        save_path=None
    ):

        if not self.analysis_results:

            raise ValueError(
                "No analysis results to save. "
                "Run data_analysis() first."
            )

        if save_path is None:

            save_path = (
                Path(__file__)
                .resolve()
                .parent.parent
                / "measure"
            )

        save_path = Path(save_path)

        save_path.mkdir(
            exist_ok=True
        )

        fdate = date.today().strftime(
            "%d_%m_%Y"
        )

        actual_time = time.strftime(
            "%H-%M-%S"
        )

        if filename is None:

            filename = (
                f"analysis_results_"
                f"{fdate}_{actual_time}.json"
            )

        filepath = save_path / filename

        utils.save_dict_json(
            self.analysis_results,
            filepath
        )

        size_mb = (
            filepath.stat().st_size
            / (1024 ** 2)
        )

        logger.info(
            f"Saved analysis : {filepath}"
        )

        logger.info(
            f"File size : {size_mb:.2f} MB"
        )

        return filepath