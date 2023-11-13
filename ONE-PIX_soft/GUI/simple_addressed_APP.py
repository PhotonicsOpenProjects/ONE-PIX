"""
Created on Wed Jul 19 18:32:47 2023

@author: Leo Brechet
"""

import customtkinter as ctk
from tkinter import filedialog
from tkinter.messagebox import showerror
import sys
import os
import glob
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import cv2
import json
import screeninfo
import PIL.ImageTk

sys.path.insert(0, os.path.abspath('../'))
from src.AcquisitionConfig import *
from src.coregistration_lib import *

window_height = 575
window_width = 825

json_path = os.path.abspath("../acquisition_param_ONEPIX.json")
print(json_path)
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
    nb_nb = int(round(nb_mask**(1/3)+.5))
    rgb_comb = 255//nb_nb
    colormap = []
    for i in range(nb_nb):
        for j in range(nb_nb):
            for k in range(nb_nb):
                colormap.append([i*rgb_comb,
                                j*rgb_comb,
                                k*rgb_comb])
    colormap = np.asarray(colormap)
 
    
    return np.uint8(colormap[:nb_mask])
    
    
class OPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.monitor_sz=screeninfo.get_monitors()[0]
        self.open_languageConfig()
        self.open_GUIConfig()
        # configure window
        self.resizable(False, False)
        self.title(f"ONEPIX GUI")
        
        x = (self.monitor_sz.width -window_width)//2-100
        y = (self.monitor_sz.height-window_height)//2-100
        if is_raspberrypi(): x,y=x+100,y+100
        self.geometry('%dx%d+%d+%d' % (window_width, window_height, x,y))
        icon_path='./logo_ONE-PIX.png' if is_raspberrypi() else './logo_ONE-PIX.ico'
        icon_path=PIL.ImageTk.PhotoImage(master=self,file=icon_path)
        self.wm_iconbitmap()
        self.iconphoto(False,icon_path)

   

        
        self.fig_vis = Figure(figsize=(8.1,3.45), dpi=100)
        self.fig_vis.patch.set_facecolor('#C4C4C4')
        gs = self.fig_vis.add_gridspec(10,50)
        self.a_vis = self.fig_vis.add_subplot(gs[:9,:20], anchor='W')
        self.b_vis = self.fig_vis.add_subplot(gs[:,22:], anchor='W')
        self.a_vis.axis('off')
        self.b_vis.axis('off')
        
        
        self.test_mode = "auto"


# =============================================================================
# 
# =============================================================================
        self.Mode_frame = ctk.CTkFrame(self)
        self.Mode_frame.grid(row=0, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan =1, sticky="nw")
        
        self.calibrationButton = ctk.CTkButton(self.Mode_frame, text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["calibrationButton"],
                                               fg_color = "#D70000", hover_color="#9D0000",
                                        command = self.do_calibration)
        
        self.calibrationButton.grid(column=0, row=0, padx=(2.5,2.5), pady=(2.5,2.5), rowspan =1, columnspan=2, sticky="we")
        self.mode_desc = ctk.CTkLabel(self.Mode_frame, text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["mode_desc"], font=('Helvetica', 18, 'bold'))
        self.mode_desc.grid(column=0, row=1, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='we')
        

        
        self.manual_choice = ctk.CTkButton(self.Mode_frame, text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["manual_choice"], fg_color="gray",
                                           state = "disabled", command = self.manual_toogle)
        self.manual_choice.grid(column=1, row=2, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.auto_choice = ctk.CTkButton(self.Mode_frame, text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["auto_choice"], state = "disabled",
                                         fg_color="gray", command = self.auto_toogle)
        self.auto_choice.grid(column=0, row=2, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='w')
    
# =============================================================================
#         
# =============================================================================
        self.Params_frame = ctk.CTkFrame(self)
        self.Params_frame.grid(row=0, column=1, pady=(2.5,2.5), rowspan =1, padx = (2.5,2.5), sticky="nw")
        
        
        
        self.KMeans_desc = ctk.CTkLabel(self.Params_frame, text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["KMeans_desc"], font=('Helvetica', 18, 'bold'))
        self.KMeans_desc.grid(column=0, row=0, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        
        self.Prim_seg_label = ctk.CTkLabel(self.Params_frame,text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["Prim_seg_label"])
        self.Prim_seg_label.grid(column=0, row=1, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.Prim_seg = ctk.CTkEntry(self.Params_frame, state = "normal")
        self.Prim_seg.insert(0,"2")
        self.Prim_seg.configure(state = "disabled", fg_color="gray")
        self.Prim_seg.grid(column=1, row=1, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        
        self.Sec_seg_label = ctk.CTkLabel(self.Params_frame,text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["Sec_seg_label"])
        self.Sec_seg_label.grid(column=0, row=2, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.Sec_seg = ctk.CTkEntry(self.Params_frame, state = "normal")
        self.Sec_seg.insert(0,"5")
        self.Sec_seg.configure(state = "disabled", fg_color="gray")
        self.Sec_seg.grid(column=1, row=2, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        
        
        
# =============================================Secondary segmentation : number of clusters================================
#         
# =============================================================================
        
        self.Acquis_frame = ctk.CTkFrame(self)
        self.Acquis_frame.grid(row=1, column=0, pady=(2.5,2.5), rowspan =1, columnspan=2, padx = (2.5,2.5), sticky='')
        self.acquireButton = ctk.CTkButton(self.Acquis_frame, text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["acquireButton"],
                                           state = 'disabled', fg_color = 'gray',
                                        command = self.acquire)
        self.acquireButton.grid(column=0, row=0, padx=(2.5,2.5), pady=(2.5,2.5), rowspan =1, columnspan=2, sticky='')

 
        
    
# =============================================================================
# =============================================================================
# =============================================================================

        self.Open_frame = ctk.CTkFrame(self)
        self.Open_frame.grid(row=2, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan =1, columnspan=2, sticky="nw")
        
        self.loadButton = ctk.CTkButton(self.Open_frame, text = self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["loadButton"],
                                        command = self.load_data)
                                        
        self.loadButton.grid(column=0, row=0, padx=(2.5,2.5), pady=(2.5,2.5),rowspan=1, columnspan=2)
        
        self.canvas_b2 = FigureCanvasTkAgg(self.fig_vis, self.Open_frame)
        self.canvas_b2.get_tk_widget().grid(column=0, row=2, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=2)

        self.toolbarFrame_b2 = ctk.CTkFrame(master=self.Open_frame, width=100, height=100)
        self.toolbarFrame_b2.grid(column=0, row=1, padx=(2.5,2.5), pady=(2.5,2.5), rowspan=1, columnspan=2, sticky = "we")
        NavigationToolbar2Tk(self.canvas_b2, self.toolbarFrame_b2)
    
    def do_calibration(self):
        self.calibrationButton.configure(state = 'normal', fg_color = "#9D0000",
                                         text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["functions"]["calibrationButton_WIP"])
        self.update()
        coregistration_calibration()
        self.manual_choice.configure(state = 'normal', fg_color = "#3B8ED0")
        self.acquireButton.configure(state = 'normal', fg_color = "#3B8ED0")
        if self.test_mode=="manual":
            self.manual_toogle()
        elif self.test_mode=="auto":
            self.auto_toogle()
        self.calibrationButton.configure(fg_color="#31D900", hover_color="#249F00",
                                         text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["calibrationButton"])

    def acquire(self):
        self.acquireButton.configure(state = 'normal', fg_color = "#9D0000",
                                     text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["functions"]["acquireButton_WIP"])
        self.update()
        f = open(json_path)
        params = json.load(f)
        f.close()
        if self.test_mode=="manual":
            params['spatial_res']='manual_segmentation'
        elif self.test_mode=="auto":
            params['spatial_res']=[int(self.Prim_seg.get()),int(self.Sec_seg.get())]
        with open(json_path, 'w') as outfile:
            json.dump(params, outfile)
            outfile.close()
        
        config=OPConfig(json_path)
        try:
            config.OP_init()
            config.thread_acquisition(time_warning=False)
            directory = '../Hypercubes'
            newest = max([os.path.join(directory,d) for d in os.listdir(directory) if d.startswith("ONE-PIX_acquisition")], key=os.path.getmtime)
            print(newest)
            self.plotMask(newest)
            self.acquireButton.configure(state = 'normal', fg_color = "#3B8ED0",
                                        text=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["acquireButton"])
        except:
            pass 
        
    def manual_toogle(self):
        self.manual_choice.configure(state = "disabled", fg_color="#3B8ED0")
        self.auto_choice.configure(state = "normal", fg_color="gray")
        self.Prim_seg.configure(state = "disabled", fg_color="gray")
        self.Sec_seg.configure(state = "disabled", fg_color="gray")
        self.test_mode = "manual"
    def auto_toogle(self):
        self.auto_choice.configure(state = "disabled", fg_color="#3B8ED0")
        self.manual_choice.configure(state = "normal", fg_color="gray")
        self.Prim_seg.configure(state = "normal", fg_color="white")
        self.Sec_seg.configure(state = "normal", fg_color="white")
        self.test_mode = "auto"
        
    def load_data(self):
        path = filedialog.askdirectory(title=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["functions"]["askdirectory"],
                                       initialdir = '../Hypercubes')
        if path !='':
            try:
                self.plotMask(path)
            except Exception as e:
                showerror(title='Loading data error',message=self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["errors"]["load_data_error"])

        
    def plotMask(self, path):
        self.a_vis.clear()
        self.b_vis.clear()
        print("maskPath : ", path)
        rawMasks = np.uint8(np.load(['/'.join([path, files]) for files in os.listdir(path) if files.startswith('mask')][0]))
        try:
            if len(self.acq_config.normalised_datacube)!=0: #Load Normalised data
                    rawSpecs = np.load(glob.glob('spectra*normalised*')[0]) 
            else:
                rawSpecs = np.load(['/'.join([path, files]) for files in os.listdir(path) if files.startswith('spectra_')][0])
        except Exception as e:
            print(e)
            rawSpecs = np.load(['/'.join([path, files]) for files in os.listdir(path) if files.startswith('spectra_')][0])

        wl = np.load(['/'.join([path, files]) for files in os.listdir(path) if files.startswith('wavelengths')][0])
        customColormap = find_rgb_label(rawMasks.shape[0])
        im = np.zeros((rawMasks.shape[1],rawMasks.shape[2],3),dtype = np.uint8)
        for i in range(1, rawMasks.shape[0]):
            mask = rawMasks[i,:,:].reshape(rawMasks.shape[1],rawMasks.shape[2],-1)
            mask = mask * customColormap[i].reshape(1,1,-1)
            im+=mask
        
        image = cv2.imread(['/'.join([path, files]) for files in os.listdir(path) if files.startswith('RGB_cor')][0])
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        customColormap = customColormap/255
        self.b_vis.imshow(image)
        self.b_vis.imshow(im, alpha = .5)
        self.b_vis.axis('off')
        for i in range(1, rawSpecs.shape[0]):
            curvColor = list(customColormap[i])
            curvColor.append(.5)
            self.a_vis.plot(wl, rawSpecs[i,:],color=curvColor)
        self.a_vis.set_xlabel(self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["functions"]["plotMask"]["xlabel"], fontsize = 10)
        self.a_vis.set_ylabel(self.widgets_text["specific_GUI"]["Addressed"]["Simple"]["functions"]["plotMask"]["ylabel"], fontsize = 10)
        self.fig_vis.canvas.draw_idle()
        
    
    def open_GUIConfig(self):
        with open(json_path, 'r') as f:
            GUI_conf = json.load(f)
            f.close()
        
        GUI_conf["pattern_method"] = "Addressing"
        
        with open(json_path, 'w') as f:
            json.dump(GUI_conf, f)
            f.close()
            
    def open_languageConfig(self):
        with open("./languages/config.json", 'r') as f:
            lang_conf = json.load(f)
            f.close()
        lang_list = lang_conf['installed_language']
        jsonFile = list(lang_list)[list(lang_list.values()).index(lang_conf["last_choice"])]
        print(jsonFile)
        
        with open(f"./languages/{jsonFile}.json", 'r') as f:
            self.widgets_text = json.load(f)
            f.close()
        # print(self.widgets_text)

    def close_window(self):
        plt.close('all')
        self.quit()
        self.destroy()


if __name__ == "__main__":
    app = OPApp()
    app.protocol("WM_DELETE_WINDOW", app.close_window)
    app.mainloop()
