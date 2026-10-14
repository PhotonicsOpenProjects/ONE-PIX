# =========================================================
# full_pipeline_acq_rec_analysis.py
# =========================================================

from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from onepix.Analysis import Analysis

import matplotlib.pyplot as plt


# =========================================================
# SPECTRAL PIPELINE
# =========================================================

pipeline_steps = [

    ("snv", {}),

    ("crop", {
        "min_wl": 600,
        "max_wl": 1800
    }),

]


# =========================================================
# ACQUISITION
# =========================================================

acq = Acquisition(
    imaging_method_name="has"
)

acq.thread_acquisition()

acq.save_raw_data()

print("\n=== ACQUISITION RESULTS ===")

print(
    list(
        acq.acquisition_results.keys()
    )
)


# =========================================================
# RECONSTRUCTION
# =========================================================

rec = Reconstruction(
    acquisition=acq.acquisition_results,
    plot_result=True
)

rec.data_reconstruction()

print("\n=== RECONSTRUCTION RESULTS ===")

print(
    list(
        rec.reconstruction_results.keys()
    )
)

print(
    "\nImaging method :",
    rec.reconstruction_results[
        "metadata"
    ][
        "imaging_method_name"
    ]
)

# =========================================================
# OPTIONAL DISPLAY
# =========================================================

if "result2plot" in rec.reconstruction_results:

    plt.figure()

    plt.imshow(
        rec.reconstruction_results[
            "result2plot"
        ]
    )

    plt.title(
        "Reconstruction result"
    )

    plt.show()


# =========================================================
# ANALYSIS
# =========================================================

ana = Analysis(
    reconstruction_dict=(
        rec.reconstruction_results
    ),
    plot_result=True
)

ana.data_analysis(
    pipeline_steps=pipeline_steps
)

print("\n=== ANALYSIS RESULTS ===")

print(
    list(
        ana.analysis_results.keys()
    )
)

print(
    "\nImaging method :",
    ana.analysis_results[
        "metadata"
    ][
        "imaging_method_name"
    ]
)

# =========================================================
# OPTIONAL DISPLAY
# =========================================================

if "result2plot" in ana.analysis_results:

    plt.figure()

    plt.imshow(
        ana.analysis_results[
            "result2plot"
        ]
    )

    plt.title(
        "Analysis result"
    )

    plt.show()