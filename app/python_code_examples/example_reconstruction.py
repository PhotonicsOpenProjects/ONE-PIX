from onepix.Reconstruction import Reconstruction

import matplotlib.pyplot as plt


# ==========================================================
# LOAD ACQUISITION JSON
# ==========================================================
acquisition_json = (r"C:\Users\grussias\Desktop\repo git\POP\ONEPIX\test_install\one-pix_private_mirror\measure\acquisition_results_28_05_2026_13-50-45.json")



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