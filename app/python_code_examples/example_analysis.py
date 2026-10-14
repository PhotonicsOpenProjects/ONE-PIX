from pathlib import Path

from onepix.Analysis import Analysis

import matplotlib.pyplot as plt


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

json_path = Path(
    r"C:\Users\grussias\Desktop\repo git\POP\ONEPIX\test_install\one-pix_private_mirror\measure\reconstruction_results_28_05_2026_17-03-08.json"
)

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