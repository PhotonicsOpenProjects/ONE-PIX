import customtkinter as ctk
from tkinter import filedialog
from tkinter.messagebox import showerror
import sys
import os
import glob
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import cv2
import json
import screeninfo
import PIL.ImageTk

sys.path.append(f"..{os.sep}..{os.sep}")
from core.Acquisition import Acquisition
from core.Reconstruction import Reconstruction
from core.Analysis import Analysis
from core.hardware.coregistration_lib import *


window_height = 575
window_width = 825

acquisition_json_path = os.path.abspath(
    f"..{os.sep}..{os.sep}conf/acquisition_parameters.json"
)
hardware_json_path = os.path.abspath(f"..{os.sep}..{os.sep}conf/hardware_config.json")
software_json_path = os.path.abspath(f"..{os.sep}..{os.sep}conf/software_config.json")


def find_rgb_label(nb_mask):
    """


    Parameters
    ----------
    nb_mask : entier
        nombre de masques à représenter.

    Returns
    -------
    colormap : tableau de uint8
        couleur RGB des masques.

    """
    nb_nb = int(round(nb_mask ** (1 / 3) + 0.5))
    rgb_comb = 255 // nb_nb
    colormap = []
    for i in range(nb_nb):
        for j in range(nb_nb):
            for k in range(nb_nb):
                colormap.append([i * rgb_comb, j * rgb_comb, k * rgb_comb])
    colormap = np.asarray(colormap)

    return np.uint8(colormap[:nb_mask])


class OPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.monitor_sz = screeninfo.get_monitors()[0]
        self.open_languageConfig()

        self.config = Acquisition()
        # configure window
        self.resizable(False, False)
        self.title(f"ONEPIX GUI")

        x = (self.monitor_sz.width - window_width) // 2 - 100
        y = (self.monitor_sz.height - window_height) // 2 - 100
        if self.config.hardware.is_raspberrypi():
            x, y = x + 100, y + 100
        self.geometry("%dx%d+%d+%d" % (window_width, window_height, x, y))
        ext = ".png" if self.config.hardware.is_raspberrypi() else ".ico"
        icon_path = f".{os.sep}imgs{os.sep}logo_ONE-PIX{ext}"
        icon_path = PIL.ImageTk.PhotoImage(master=self, file=icon_path)
        self.wm_iconbitmap()
        self.iconphoto(False, icon_path)

        self.fig_vis = Figure(figsize=(8.1, 3.45), dpi=100)
        self.fig_vis.patch.set_facecolor("#C4C4C4")
        gs = self.fig_vis.add_gridspec(10, 50)
        self.a_vis = self.fig_vis.add_subplot(gs[:9, :20], anchor="W")
        self.b_vis = self.fig_vis.add_subplot(gs[:, 22:], anchor="W")
        self.a_vis.axis("off")
        self.b_vis.axis("off")

        self.test_mode = "auto"

        # =============================================================================
        #
        # =============================================================================
        self.Mode_frame = ctk.CTkFrame(self)
        self.Mode_frame.grid(
            row=0, column=0, pady=(2.5, 2.5), padx=(2.5, 2.5), rowspan=1, sticky="nw"
        )

        self.calibrationButton = ctk.CTkButton(
            self.Mode_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "calibrationButton"
            ],
            fg_color="#D70000",
            hover_color="#9D0000",
            command=self.do_calibration,
        )

        self.calibrationButton.grid(
            column=0,
            row=0,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=2,
            sticky="we",
        )
        self.mode_desc = ctk.CTkLabel(
            self.Mode_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["mode_desc"],
            font=("Helvetica", 18, "bold"),
        )
        self.mode_desc.grid(
            column=0,
            row=1,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="we",
        )

        self.manual_choice = ctk.CTkButton(
            self.Mode_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "manual_choice"
            ],
            fg_color="gray",
            state="disabled",
            command=self.manual_toogle,
        )
        self.manual_choice.grid(
            column=1,
            row=2,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="w",
        )
        self.auto_choice = ctk.CTkButton(
            self.Mode_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "auto_choice"
            ],
            state="disabled",
            fg_color="gray",
            command=self.auto_toogle,
        )
        self.auto_choice.grid(
            column=0,
            row=2,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="w",
        )

        # =============================================================================
        #
        # =============================================================================
        self.Params_frame = ctk.CTkFrame(self)
        self.Params_frame.grid(
            row=0, column=1, pady=(2.5, 2.5), rowspan=1, padx=(2.5, 2.5), sticky="nw"
        )

        self.KMeans_desc = ctk.CTkLabel(
            self.Params_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "KMeans_desc"
            ],
            font=("Helvetica", 18, "bold"),
        )
        self.KMeans_desc.grid(
            column=0,
            row=0,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="w",
        )

        self.Prim_seg_label = ctk.CTkLabel(
            self.Params_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "Prim_seg_label"
            ],
        )
        self.Prim_seg_label.grid(
            column=0,
            row=1,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="w",
        )
        self.Prim_seg = ctk.CTkEntry(self.Params_frame, state="normal", width=60)
        self.Prim_seg.insert(0, "2")
        self.Prim_seg.configure(state="disabled", fg_color="gray")
        self.Prim_seg.grid(
            column=1,
            row=1,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="w",
        )

        self.Sec_seg_label = ctk.CTkLabel(
            self.Params_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "Sec_seg_label"
            ],
        )
        self.Sec_seg_label.grid(
            column=0,
            row=2,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="w",
        )
        self.Sec_seg = ctk.CTkEntry(self.Params_frame, state="normal", width=60)
        self.Sec_seg.insert(0, "5")
        self.Sec_seg.configure(state="disabled", fg_color="gray")
        self.Sec_seg.grid(
            column=1,
            row=2,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=1,
            sticky="w",
        )

        # =============================================Secondary segmentation : number of clusters================================
        #
        # =============================================================================

        self.Acquis_frame = ctk.CTkFrame(self)
        self.Acquis_frame.grid(
            row=1,
            column=0,
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=2,
            padx=(2.5, 2.5),
            sticky="",
        )
        self.acquireButton = ctk.CTkButton(
            self.Acquis_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "acquireButton"
            ],
            state="disabled",
            fg_color="gray",
            command=self.acquire,
        )
        self.acquireButton.grid(
            column=0,
            row=0,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=2,
            sticky="",
        )

        # =============================================================================
        # =============================================================================
        # =============================================================================

        self.Open_frame = ctk.CTkFrame(self)
        self.Open_frame.grid(
            row=2,
            column=0,
            pady=(2.5, 2.5),
            padx=(2.5, 2.5),
            rowspan=1,
            columnspan=2,
            sticky="nw",
        )

        self.loadButton = ctk.CTkButton(
            self.Open_frame,
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["loadButton"],
            command=self.load_data,
        )

        self.loadButton.grid(
            column=0, row=0, padx=(2.5, 2.5), pady=(2.5, 2.5), rowspan=1, columnspan=2
        )

        self.canvas_b2 = FigureCanvasTkAgg(self.fig_vis, self.Open_frame)
        self.canvas_b2.get_tk_widget().grid(
            column=0, row=2, padx=(2.5, 2.5), pady=(2.5, 2.5), rowspan=1, columnspan=2
        )

        self.toolbarFrame_b2 = ctk.CTkFrame(
            master=self.Open_frame, width=100, height=100
        )
        self.toolbarFrame_b2.grid(
            column=0,
            row=1,
            padx=(2.5, 2.5),
            pady=(2.5, 2.5),
            rowspan=1,
            columnspan=2,
            sticky="we",
        )
        NavigationToolbar2Tk(self.canvas_b2, self.toolbarFrame_b2)

    def do_calibration(self):
        self.calibrationButton.configure(
            state="normal",
            fg_color="#9D0000",
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["functions"][
                "calibrationButton_WIP"
            ],
        )
        self.update()
        coregistration_calibration()
        self.manual_choice.configure(state="normal", fg_color="#3B8ED0")
        self.acquireButton.configure(state="normal", fg_color="#3B8ED0")
        if self.test_mode == "manual":
            self.manual_toogle()
        elif self.test_mode == "auto":
            self.auto_toogle()
        self.calibrationButton.configure(
            fg_color="#31D900",
            hover_color="#249F00",
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                "calibrationButton"
            ],
        )

    def json_actualisation(self):
        with open(acquisition_json_path) as f:
            params = json.load(f)

        with open(software_json_path) as f:
            software_params = json.load(f)

        if self.test_mode == "manual":
            software_params["clustering_method"] = "LabelMe"
        elif self.test_mode == "auto":
            software_params["clustering_method"] = "Kmeans"
            software_params["clustering_parameters"] = [
                int(self.Prim_seg.get()),
                int(self.Sec_seg.get()),
            ]

        with open(acquisition_json_path, "w") as outfile:
            json.dump(params, outfile, indent=4)

        with open(software_json_path, "w") as outfile:
            json.dump(software_params, outfile, indent=4)

    def params_actualisation(self):
        self.json_actualisation()
        try:
            self.config.hardware.spectrometer.spec_close()
        except Exception:
            pass
        del self.config
        self.config = Acquisition()
        self.config.hardware.spectrometer.spec_open()
        self.config.hardware.spectrometer.integration_time_ms = (
            self.config.hardware.spectrometer.integration_time_ms
        )
        self.config.hardware.spectrometer.set_integration_time()

    def acquire(self):
        self.acquireButton.configure(
            state="normal",
            fg_color="#9D0000",
            text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["functions"][
                "acquireButton_WIP"
            ],
        )
        self.update()
        self.params_actualisation()

        try:
            self.config.hardware.projection.get_integration_time_auto(self.config)
            if self.config.periode_pattern < 60:
                self.config.periode_pattern = 60
            self.config.thread_acquisition(time_warning=False)
            self.config.save_raw_data()
            directory = f"..{os.sep}Hypercubes"
            newest = max(
                [
                    os.path.join(directory, d)
                    for d in os.listdir(directory)
                    if d.startswith("ONE-PIX")
                ],
                key=os.path.getmtime,
            )
            print(newest)
            self.load_data(newest)
            self.acquireButton.configure(
                state="normal",
                fg_color="#3B8ED0",
                text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"][
                    "acquireButton"
                ],
            )
        except Exception as e:
            print(e)

    def manual_toogle(self):
        self.manual_choice.configure(state="disabled", fg_color="#3B8ED0")
        self.auto_choice.configure(state="normal", fg_color="gray")
        self.Prim_seg.configure(state="disabled", fg_color="gray")
        self.Sec_seg.configure(state="disabled", fg_color="gray")
        self.test_mode = "manual"

    def auto_toogle(self):
        self.auto_choice.configure(state="disabled", fg_color="#3B8ED0")
        self.manual_choice.configure(state="normal", fg_color="gray")
        self.Prim_seg.configure(state="normal", fg_color="white")
        self.Sec_seg.configure(state="normal", fg_color="white")
        self.test_mode = "auto"

    def load_data(self, path=None):
        if path is None:
            path = filedialog.askdirectory(
                title=self.widgets_text["specific_GUI"]["Addressed"]["Advanced"][
                    "functions"
                ]["askdirectory"],
                initialdir="../Hypercubes",
            )
        if path != "":
            try:
                self.analysis = Analysis(
                    data_path=path
                ).imaging_method.image_analysis_method
                # self.analysis.load_reconstructed_data()
                self.plotMask()
            except Exception as e:
                showerror(
                    title="Loading data error",
                    message=self.widgets_text["specific_GUI"]["Addressed"]["Advanced"][
                        "errors"
                    ]["load_data_error"],
                )
            """"
            try:
                if len(self.config.normalised_datacube)!=0: #Load Normalised data
                    rawSpecs = np.load(glob.glob(os.path.abspath(f'{path}/spectra*normalised*'))[0]) 
                else:
                    rawSpecs = np.load(['/'.join([path, files]) for files in os.listdir(path) if files.startswith('spectra_')][0])
            except Exception as e:
                print(e)
                rawSpecs = np.load(['/'.join([path, files]) for files in os.listdir(path) if files.startswith('spectra_')][0])
            """

    def plotMask(self):
        self.a_vis.clear()
        self.b_vis.clear()

        customColormap = find_rgb_label(self.analysis.clusters.shape[0])
        im = np.zeros(
            (self.analysis.clusters.shape[1], self.analysis.clusters.shape[2], 3),
            dtype=np.uint8,
        )
        for i in range(1, self.analysis.clusters.shape[0]):
            mask = self.analysis.clusters[i, :, :].reshape(
                self.analysis.clusters.shape[1], self.analysis.clusters.shape[2], -1
            )
            mask = mask * customColormap[i].reshape(1, 1, -1)
            im += mask

        spectra = self.analysis.reconstructed_data

        image = cv2.cvtColor(self.analysis.rgb_image, cv2.COLOR_BGR2RGB)
        customColormap = customColormap / 255
        self.b_vis.imshow(image)
        self.b_vis.imshow(im, alpha=0.5)
        self.b_vis.axis("off")

        for i in range(1, spectra.shape[0]):
            curvColor = list(customColormap[i])
            curvColor.append(0.5)
            self.a_vis.plot(self.analysis.wavelengths, spectra[i, :], color=curvColor)
        self.a_vis.legend(self.analysis.patterns_order[1:-1])
        self.a_vis.set_xlabel(
            self.widgets_text["specific_GUI"]["Addressed"]["Advanced"]["functions"][
                "plotMask"
            ]["xlabel"],
            fontsize=10,
        )
        self.a_vis.set_ylabel(
            self.widgets_text["specific_GUI"]["Addressed"]["Advanced"]["functions"][
                "plotMask"
            ]["ylabel"],
            fontsize=10,
        )
        self.fig_vis.canvas.draw_idle()

    def open_languageConfig(self):
        with open("./languages/config.json", "r") as f:
            lang_conf = json.load(f)

        lang_list = lang_conf["installed_language"]
        jsonFile = list(lang_list)[
            list(lang_list.values()).index(lang_conf["last_choice"])
        ]
        print(jsonFile)

        with open(f"./languages/{jsonFile}.json", "r") as f:
            self.widgets_text = json.load(f)

    def close_window(self):
        plt.close("all")
        self.quit()
        self.destroy()


if __name__ == "__main__":
    app = OPApp()
    app.protocol("WM_DELETE_WINDOW", app.close_window)
    app.mainloop()
