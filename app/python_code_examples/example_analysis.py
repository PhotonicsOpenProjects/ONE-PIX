import sys
from pathlib import Path

from onepix.Analysis import Analysis

import matplotlib.pyplot as plt


def latest_measure(pattern):
    """The file given on the command line, else the newest measure/ file matching `pattern`."""
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    measure_dir = Path(__file__).resolve().parents[2] / "measure"
    files = sorted(measure_dir.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not files:
        sys.exit(f"No {pattern} in {measure_dir}: run an acquisition first, or pass a file as argument.")
    return files[-1]


# =========================================================
# PIPELINE
# =========================================================

pipeline_steps = [

    ("snv", {}),

    ("crop", {
        "min_wl": 450,
        "max_wl": 850
    }),

    ("indices", {
        "indices": [
            "ndvi",
            "ndci",
            "pri_531_570",
            "ci_green",
            "mtci",
            "mcari",
            "reip"
        ]
    }),

]


# =========================================================
# LOAD RECONSTRUCTION JSON
# =========================================================

json_path = latest_measure("reconstruction_results_*.json")

ana = Analysis(
    reconstruction_dict=json_path,
    plot_result=True
)


# =========================================================
# RUN PIPELINE
# =========================================================

ana.data_analysis(
    pipeline_steps=pipeline_steps
)


# =========================================================
# PRINT RESULTS
# =========================================================

print("\n=== ANALYSIS RESULTS ===")

for key, value in ana.analysis_results.items():

    if key == "result2plot":
        print(
            f"{key}: shape={value.shape}"
        )

    else:
        print(f"{key}: {value}")


# =========================================================
# DISPLAY MOSAIC
# =========================================================

if "result2plot" in ana.analysis_results:

    plt.figure(
        figsize=(12, 12)
    )

    plt.imshow(
        ana.analysis_results[
            "result2plot"
        ]
    )

    plt.axis(
        "off"
    )

    plt.title(
        "Analysis results"
    )

    plt.show()