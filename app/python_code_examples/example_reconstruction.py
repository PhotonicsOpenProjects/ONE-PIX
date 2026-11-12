import sys
from pathlib import Path

from onepix.Reconstruction import Reconstruction

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


# ==========================================================
# LOAD ACQUISITION JSON
# ==========================================================
acquisition_json = latest_measure("acquisition_results_*.json")



# ==========================================================
# RECONSTRUCTION
# ==========================================================
rec = Reconstruction(
    acquisition=acquisition_json,
    plot_result=True
)

rec.data_reconstruction()


# ==========================================================
# DISPLAY RESULT2PLOT
# ==========================================================
if "result2plot" in rec.reconstruction_results:

    result = rec.reconstruction_results[
        "result2plot"
    ]

    plt.figure(figsize=(14, 6))

    plt.imshow(result)

    plt.title("ONE-PIX Reconstruction")

    plt.axis("off")

    plt.tight_layout()

    plt.show()

else:

    print("⚠️ result2plot not found")


# ==========================================================
# SAVE RECONSTRUCTION
# ==========================================================
rec.save_reconstruction_results()


print("✅ Full reconstruction pipeline OK")