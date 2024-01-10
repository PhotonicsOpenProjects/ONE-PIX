"""
@author:PhotonicsOpenProjects
Modified and traducted by Leo Brecheton Wed Jul 19 18:32:47 2023

"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter.messagebox import showwarning

from functools import partial
import PIL.Image, PIL.ImageTk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as CM
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib import rcParams

rcParams.update({'figure.autolayout': True})
rcParams['axes.edgecolor'] = '#ffffff'
rcParams['xtick.color']='white'
rcParams['ytick.color']='white'

import sys
import os
import glob
import datetime
from datetime import date
import time

sys.path.append(f'..{os.sep}..{os.sep}')

from core.Acquisition import Acquisition
from core.Reconstruction import Reconstruction
from core.Analysis import Analysis
import numpy as np
import matplotlib.pyplot as plt
import xarray as xr
import pandas as pd
import spyndex as sp
import tifffile as tiff
import cv2
from scipy import interpolate
import json
import customtkinter as ctk
import threading
import screeninfo
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

VERSION = '2.0.0'
root_path = os.getcwd()
acquisition_json_path = os.path.abspath(f'..{os.sep}..{os.sep}conf/acquisition_parameters.json')
hardware_json_path = os.path.abspath(f'..{os.sep}..{os.sep}conf/hardware_config.json')
software_json_path = os.path.abspath(f'..{os.sep}..{os.sep}conf/software_config.json')


window_height = 600
window_width = 1020


class OPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.monitor_sz=screeninfo.get_monitors()[0]
        self.open_languageConfig()
        #self.open_GUIConfig()
        self.acq_config=Acquisition()
        # configure window
        self.resizable(False, False)
        self.title(f"ONEPIX GUI {VERSION}")
        x = (self.monitor_sz.width//2) - (window_width//2)-100
        y = (self.monitor_sz.height//2) - (window_height//2)-100
        if self.acq_config.hardware.is_raspberrypi(): x,y=x+100,y+100
        self.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))
        ext=".png" if self.acq_config.hardware.is_raspberrypi() else ".ico"
        icon_path=f'.{os.sep}imgs{os.sep}logo_ONE-PIX{ext}'
        icon_path=PIL.ImageTk.PhotoImage(master=self,file=icon_path)
        self.wm_iconbitmap()
        self.iconphoto(False,icon_path)

        
        # create tabviews
        self.tabview = ctk.CTkTabview(self, width=window_width,height=window_height)
        self.tabview.grid(row=1, column=1)
        self.tabview.add(self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["title"])
        # self.tabview.add(self.widgets_text["specific_GUI"]["complete"]["Analysis_tab"]["title"])
        self.tabview.add(self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["title"])
# =============================================================================
#         Acquisition tab
# =============================================================================

         ###################################################
         #                      #                          #
         #                      #                          #
         #        block 1       #                          #
         #                      #         block 3          #
         ########################                          #
         #                      #                          #
         #     block 2          #                          #
         ###################################################

            
        self.acquisition_tab=self.tabview.tab(self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["title"])
        
        #configure grid layout (4x4)
        self.acquisition_tab.grid_columnconfigure(2, weight=1)
        self.acquisition_tab.grid_columnconfigure((0,1), weight=0)
        self.acquisition_tab.grid_rowconfigure((0,1,2,3,4,5), weight=1)


        self.proj=0
        self.copy_of_pil_img=0
        self.label_test_proj=0
        
        self.res=0 #init result dictionaries
        self.acq_res=0

        # =====================================================================
        #         block 1
        # =====================================================================
        
        # create acquisition settings frame
        self.acq_mode_frame = ctk.CTkFrame(self.acquisition_tab)
        self.acq_mode_frame.grid(row=0, column=0,rowspan=1, padx=(10, 10), pady=(20, 0), sticky="nsew")
        self.label_acq_mode = ctk.CTkLabel(master=self.acq_mode_frame, text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 2"]["title"], font=ctk.CTkFont(size=16, weight="bold"))
        self.label_acq_mode.grid(row=0, column=0, columnspan=1, padx=10, pady=10)
        
        self.entry_img_res = ctk.CTkEntry(self.acq_mode_frame,width=45)
        self.entry_img_res.insert(0,str(self.acq_config.spatial_res))
        self.entry_img_res.grid(row=3, column=0, pady=0, padx=100)
        self.label_img_res =ctk.CTkLabel(self.acq_mode_frame, text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 2"]["label_img_res"])
        self.label_img_res.grid(row=2, column=0, pady=0, padx=0)
        
               
        self.methods_list=glob.glob(r"../../plugins/imaging_methods/*")
        self.methods_list=[x[30:] for x in self.methods_list]
        self.methods_list=[m for m in self.methods_list if m not in ["Addressing","Abstract","FIS_common_functions"]]
        
        self.spectro_list=glob.glob(r"../../plugins/spectrometer/*")
        self.spectro_list=[x[27:] for x in self.spectro_list]
        try:
            self.spectro_list.remove('__init__.py')
            self.spectro_list.remove('Abstract')
            self.spectro_list.remove('__pycache__')
        except ValueError:
            pass

        self.methods_optionemenu = ctk.CTkOptionMenu(self.acq_mode_frame, values=self.methods_list)
        self.methods_optionemenu.grid(row=2, column=1, padx=(2.5,2.5), pady=(2.5,2.5))
        self.methods_optionemenu.set('FourierSplit')
                
        self.switch_spectro = ctk.CTkSwitch(master=self.acq_mode_frame,text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 2"]["switch_spectro"],
                                            text_color='red',command=self.switch_spectro_command)
        self.switch_spectro.deselect()
        self.switch_spectro.grid(row=0,column=1, padx=(2.5,2.5), pady=(2.5,2.5))
        
        self.button_co = ctk.CTkButton(self.acq_mode_frame, text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 2"]["button_co"],state='normal',height=40,command=self.spec_connection)
        self.button_co.grid(row=3, column=1,sticky='n')
        
        self.button_acquire_hyp = ctk.CTkButton(self.acq_mode_frame, text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 2"]["button_acquire_hyp"],
                                                state='disabled',height=40,command=self.thread_acquire_hyp)
        self.button_acquire_hyp.grid(row=4, column=0, columnspan = 2, pady=(40,0))
        self.process=0
        self.process_alive=False
        self.spec_connection()
        self.update()
        
        # =====================================================================
        #         block 2
        # =====================================================================
        # create progressbar frame
        self.appearence_frame = ctk.CTkFrame(self.acquisition_tab)
        self.appearence_frame.grid(row=1, column=0, rowspan=1, padx=(10, 10), pady=(20, 0), sticky='we')
        self.appearance_mode_label = ctk.CTkLabel(self.appearence_frame, text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 4"]["appearance_mode_label"], anchor="w")
        self.appearance_mode_label.grid(row=0, column=0, sticky = 'w')
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.appearence_frame, values=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 4"]["appearance_mode_optionemenu"], 
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=1, column=0, padx=0, pady=(0, 10))
        
        # self.pg_bar_frame = ctk.CTkFrame(self.acquisition_tab)
        # self.pg_bar_frame.grid(row=2, column=0,padx=(150,0),pady=(20,0))
        self.progressbar= ctk.CTkProgressBar(self.appearence_frame)
        self.progressbar.grid(row=1, column=1,pady=10, padx = (50,0))
        self.progressbar.set(value=0)
        self.est_time_label=ctk.CTkLabel(self.appearence_frame, text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 5"]["est_time_label"],anchor='w', font=ctk.CTkFont( weight="bold"))
        self.est_time_label.grid(row=0, column=1,pady=(0,0), padx = (50,0))
        
        # =====================================================================
        #         block 3
        # =====================================================================
        # create Display frame
        self.display_frame = ctk.CTkFrame(self.acquisition_tab)
        self.display_frame.grid(row=0, column=2,columnspan=2,rowspan=8, pady=(20, 0),padx=(0,0), sticky="nsew")
        self.label_disp_mode = ctk.CTkLabel(master=self.display_frame, text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 3"]["title"],
                                            font=ctk.CTkFont(size=16, weight="bold"))
        self.label_disp_mode.grid(row=0, column=0,sticky='w',padx=(20,0),pady=10)

        self.fig = Figure(figsize=(5,4), dpi=100)
        self.fig.patch.set_facecolor('#2D2D2D')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.display_frame)  # A tk.DrawingArea.
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1,column=0,padx=20,pady=5,sticky="")
        self.a_acq= self.fig.add_subplot(111)
        self.a_acq.set_axis_off()
                
        self.switch_spat2im = ctk.CTkSwitch(master=self.display_frame,text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 3"]["switch_spat2im"],
                                            command=self.switch_spat2im_command,state='disabled')
        self.switch_spat2im.grid(row=0,column=0,sticky='w',padx=120)

        
        
# =============================================================================
#         VI Analysis tab
# =============================================================================

            ###############################################
            #          block 1         #     block2       #
            ###############################################
            #                  #                          #
            #     block 3      #                          #
            #                  #                          #
            ####################          block 5         #
            #                  #                          #
            #     block 4      #                          #
            #                  #                          #
            ###############################################

    
        self.VI=self.tabview.tab(self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["title"])
    
        self.IDXS = None
        self.shown_IDX = None
        self.shown_band = None
        self.save_path = None
        self.id_SaveFormat = None
        self.bands_SaveFormat = None
        self.save_comment = ctk.StringVar()
        self.chkSave_id = ctk.IntVar()
        self.chkSave_id.set(1)
        self.chkSave_bands = ctk.IntVar()
        self.chkSave_bands.set(0)
        
        # figure création for bands preview
        self.bands_graph = Figure(figsize=(2.8,2), dpi=100)
        self.bands_graph.patch.set_facecolor('#2D2D2D')
        self.bands_subplot = self.bands_graph.add_subplot(111)
        self.bands_subplot.axis('off')
        
        # figure creation for index
        self.f = Figure(figsize=(3.8,2.5), dpi=100)
        self.f.patch.set_facecolor('#2D2D2D')
        gs = self.f.add_gridspec(1,50)
        self.a = self.f.add_subplot(gs[:,:-10], anchor='W')
        self.color = self.f.add_subplot(gs[:,-10], anchor='W')
        self.color.tick_params(labelsize=6)
        self.a.axis('off')
        self.color.axis('off')
        
        
        # =====================================================================
        #         Block 1
        # =====================================================================
        self.loadfiles_frame=ctk.CTkFrame(self.VI,width=window_width)
        self.loadfiles_frame.grid(row=0, column=0, padx=40, pady=10, rowspan =1, columnspan=3,sticky='nsew')
        
        self.sat_desc = ctk.CTkLabel(self.loadfiles_frame, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 1"]["sat_desc"])
        self.sat_desc.grid(column=0, row=0)
        self.shown_sat_path = ctk.StringVar()
        self.path_to_csv = '/'.join(['/'.join(os.path.abspath(os.curdir).split('\\')),'Sentinel2B.csv'])
        self.shown_sat_path.set('/'.join(self.path_to_csv.split('/')[-3:]))
        self.shown_data_path = ctk.StringVar()
        self.shown_data_path.set(self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 1"]["shown_data_path"])
        
        self.sat_path = self.path_to_csv
        self.sat_path_label = ctk.CTkEntry(self.loadfiles_frame, textvariable = self.shown_sat_path,
                                           state = 'readonly',width=300,text_color='white')
        self.sat_path_label.grid(column=1, row=0, padx=10, pady=(2.5,2.5), rowspan =1, columnspan=1,sticky='e')
        self.sat_bouton = ctk.CTkButton(self.loadfiles_frame, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 1"]["explore_bouton"],
                                        command = lambda : self.get_path("sat"))
        self.sat_bouton.grid(column=2, row=0, padx=10, pady=(2.5,2.5), rowspan =1, columnspan=1,sticky='w')
        
        
        self.data_path = ''
        self.data_desc = ctk.CTkLabel(self.loadfiles_frame, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 1"]["data_desc"])
        self.data_desc.grid(column=0, row=1,sticky='e')
        self.data_path_label = ctk.CTkEntry(self.loadfiles_frame, textvariable = self.shown_data_path,
                                            state = 'readonly',width=300,text_color='red')
        self.data_path_label.grid(column=1, row=1, padx=10, pady=(2.5,2.5), rowspan =1, columnspan=1,sticky='e')
        self.data_bouton = ctk.CTkButton(self.loadfiles_frame, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 1"]["explore_bouton"],
                                         command = lambda : self.get_path("data"))
        self.data_bouton.grid(column=2, row=1, padx=10, pady=(2.5,2.5), rowspan =1, columnspan=1,sticky='w')

        
        
          

        # =====================================================================
        #         Block 2
        # =====================================================================
        self.seldomain_frame = ctk.CTkFrame(self.VI)
        self.seldomain_frame.grid(row=0, column=3, pady=10, rowspan =1, sticky="w")
        
        self.domain_desc = ctk.CTkLabel(self.seldomain_frame,text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 2"]["domain_desc"])
        self.domain_desc.grid(column=0, row=0, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=1)
        test = ctk.CTkButton(self.seldomain_frame, text = "?",
                             font=(tk.font.nametofont("TkDefaultFont"),20),text_color='red', width =12)
        test.grid(column=1, row=0, padx=30, pady=(10,2.5), rowspan=1, columnspan=1)
        self.domain = ctk.CTkComboBox(self.seldomain_frame)
        self.domain.configure(values=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 2"]["domain"])
        self.domain.set("vegetation") #index de l'élément sélectionné
        self.domain.grid(column=0, row=1, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=1)  
        
        
        # =====================================================================
        #         Block 4
        # =====================================================================
        self.preview_frame = ctk.CTkFrame(self.VI)
        self.preview_frame.grid(row=2, column=0, pady=(5,5), rowspan =1)
        
        self.canvas_b3 = FigureCanvasTkAgg(self.bands_graph, self.preview_frame)
        self.canvas_b3.get_tk_widget().grid(column=0, row=2, padx=10, pady=10,rowspan=1, columnspan=5)
        self.toolbarFrame_bX = ctk.CTkFrame(master=self.preview_frame, width=100, height=100)
        self.toolbarFrame_bX.grid(column=0, row=1, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=5)
        NavigationToolbar2Tk(self.canvas_b3, self.toolbarFrame_bX)
        
        self.bands_list = AutocompleteCombobox(self.preview_frame)
        self.bands_list["state"]= "disabled" # initialement grise
        self.bands_list.set_completion_list([''])
        self.bands_list.grid(column=0, row=0, padx=10, pady=10)
        for binds in [self.bands_list]:
            self.bands_list.bind("<<ComboboxSelected>>", lambda event=None:
                         self.get_combobox_value("bands"))
            self.bands_list.bind("<Return>", lambda event=None:
                         self.get_combobox_value("bands"))
        
        self.bands_scale = tk.Scale(self.preview_frame, orient='horizontal', from_=0, to_=0, length=200,
                          showvalue = 0, state = "disabled",
                          repeatdelay = 100,
                          command = self.plot_bands, var = self.shown_band)
        self.bands_scale.grid(column=1, row=0, padx=10, pady=10, rowspan=1, columnspan=3)
        
        



        # =====================================================================
        #         Block 3
        # =====================================================================
        self.commands_frame=ctk.CTkFrame(self.VI)
        self.commands_frame.grid(row=1, column=0, pady=10, rowspan =1)

        self.sort_choice = ttk.Combobox(self.commands_frame, textvariable=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["sort_choice"],
                                   state = "readonly")
        self.sort_choice['values']=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["sort_choice"]
        self.sort_choice.current(0) #index de l'élément sélectionné
        self.sort_choice.grid(column=0, row=1, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=1)        
        self.sort_choice.bind("<<ComboboxSelected>>", lambda event=None:
                         self.get_mode_choice())
            
        self.critere = ctk.CTkComboBox(self.commands_frame, values= self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["critere"], state = "readonly")
        self.critere.set(self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["critere"][0]) #index de l'élément sélectionné
        self.critere.configure(state = "disable")
        self.critere.grid(column=0, row=2, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=1)
        
        self.nb_keep = ctk.CTkEntry(self.commands_frame, state = "disabled")
        self.nb_keep.grid(column=1, row=2, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=1)
        
        self.calc_bouton = ctk.CTkButton(self.commands_frame , text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["calc_bouton"], 
                            state = "disabled",command = self.calculation)
                           
        self.calc_bouton.grid(column=1, row=1, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=1)

        self.WIP = ctk.CTkLabel(self.commands_frame, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["WIP"])
        self.WIP.grid(column=0, row=3, padx=10, pady=(2.5,2.5), rowspan=1, columnspan=1)

            
        # =====================================================================
        #         Block 5
        # =====================================================================
        self.indices_frame=ctk.CTkFrame(self.VI,width=250,height=600)
        self.indices_frame.grid(row=1, column=1,padx=10, pady=10, rowspan =2, columnspan=3,sticky='NW')

        self.canvas_b5 = FigureCanvasTkAgg(self.f, self.indices_frame)
        self.canvas_b5.get_tk_widget().grid(column=0, row=2, padx=10, pady=10,rowspan=1, columnspan=2)

        self.toolbarFrame = ctk.CTkFrame(master=self.indices_frame, width=100, height=100)
        self.toolbarFrame.grid(column=0, row=1, padx=10, pady=10, rowspan=1, columnspan=2)
        NavigationToolbar2Tk(self.canvas_b5, self.toolbarFrame)
        
        self.indice_list = AutocompleteCombobox(self.indices_frame)
        self.indice_list.configure(state = "disabled") # initialement grise
        self.indice_list.set_completion_list([''])
        self.indice_list.grid(column=0, row=0, padx=10, pady=10)
        for binds in [self.indice_list]:
            self.indice_list.bind("<<ComboboxSelected>>", lambda event=None:
                         self.get_combobox_value("idx"))
            self.indice_list.bind("<Return>", lambda event=None:
                         self.get_combobox_value("idx"))
        
        self.indices_scale = tk.Scale(self.indices_frame, orient='horizontal', from_=0, to_=0, length=200,
                          showvalue = 0, state = "disabled",
                          repeatdelay = 100,
                          command = self.plot_indices, var = self.shown_IDX)
        self.indices_scale.grid(column=1, row=0, padx=10, pady=10, rowspan=1, columnspan=3)
        
        self.save_options = ctk.CTkButton(self.indices_frame, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 5"]["save_options"], state = "disabled",
                                       command = self.save_menu)
        self.save_options.grid(column=0, row=3, padx=50, pady=10,sticky='e')
        
        self.save_confirm = ctk.CTkButton(self.indices_frame, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 5"]["save_confirm"],state = "disabled",
                                      command = self.save_data)
        
        self.save_confirm.grid(column=1, row=3, padx=(0,20), pady=10)
    
   
    
# =============================================================================
#         Acquisition's tab functions
# =============================================================================
       
    
    def change_appearance_mode_event(self, new_appearance_mode: str):
        List = ["Dark", "Light"]
        trad_themes = self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 4"]["appearance_mode_optionemenu"]
        print(self.appearance_mode_optionemenu.get())
        ctk.set_appearance_mode(List[trad_themes.index(self.appearance_mode_optionemenu.get())])
       
    
    def clear_graph_tab1(self):
        
        self.fig.clear() 
        self.a_acq.clear()
        self.a_acq= self.fig.add_subplot(111)
        self.a_acq.cla()
        self.a_acq.set_axis_off()
        self.canvas.draw_idle()
        self.switch_spat2im.configure(state='disabled')
        
  
    def close_window(self):
        if messagebox.askokcancel(self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["functions"]["askokcancel"]["title"],
                                  self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["functions"]["askokcancel"]["confirm"]):
            if self.acq_config.hardware.spectrometer.DeviceName != '':
                self.acq_config.hardware.spectrometer.spec_close()
            plt.close('all')
            self.quit()
            self.destroy()
 
 
    def close_window_proj(self):
        try:
            self.proj.destroy()
        except (AttributeError,RuntimeError,tk._tkinter.TclError):
            pass
 
    def _resize_image(self,event):
        img_pil = self.copy_of_pil_img.resize((self.proj.winfo_width() - 100, self.proj.winfo_height() - 100))
 
        img = PIL.ImageTk.PhotoImage(master=self.proj, image=img_pil)
        self.label_test_proj.config(image=img)
        self.label_test_proj.image = img
 
 
    def window_size_test(self):      
        self.proj = ctk.CTkToplevel()
        self.proj.geometry("{}x{}+{}+{}".format(self.acq_config.width, self.acq_config.height, screenWidth, 0))
        self.proj.update()
        y = list(range(self.acq_config.height))  # horizontal vector for the pattern creation
        x = list(range(self.acq_config.width))  # vertical vector for the pattern creation

        Y, X = np.meshgrid(x, y)  # horizontal and vertical array for the pattern creation
        A = 2 * np.pi * X * 10 / self.acq_config.height
        B = 2 * np.pi * Y * 10 / self.acq_config.width
        pos_r = np.cos(A + B)  # gray pattern creation
        pos_r[pos_r < 0] = 0
 
        pil_img = PIL.Image.fromarray(255 * pos_r)
 
        img = PIL.ImageTk.PhotoImage(master=self.proj, image=pil_img)
        self.label_test_proj = tk.Label(self.proj, image=img)
        self.label_test_proj.image = img
 
#         self.label_test_proj.bind('<Configure>', self._resize_image)
        self.label_test_proj.pack()
        self.proj.protocol("WM_DELETE_WINDOW", partial(self.close_window_proj))
        
 
    def switch_spectro_command(self):
        if self.switch_spectro.get()==0:
            self.switch_spectro.select()
        else:
            self.switch_spectro.deselect()
    
    def switch_spat2im_command(self):
        self.clear_graph_tab1()
        self.switch_spat2im.configure(state='normal')
        
        if self.switch_spat2im.get()==0:
            #display spectra
            self.a_acq.imshow(np.log10(abs(np.mean(self.acq_res.whole_spectrum,2))))
            self.a_acq.set_title(self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["functions"]["switch_spat2im_command"]["freq"],color='white')
        else:
            #display image
            self.a_acq.imshow(self.acq_res.rgb_image)
            self.a_acq.set_title(self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["functions"]["switch_spat2im_command"]["spat"],color='white')
       
            
    def spec_connection(self):
        test = 0
        for i in self.spectro_list:
            if test==0:
                try:
                    self.acq_config.hardware.name_spectro = i
                    self.acq_config.hardware.spectrometer.spec_open()
             
                    if self.acq_config.hardware.spectrometer.DeviceName != '':
                        test = 1
                        spectro_name=self.acq_config.hardware.spectrometer.DeviceName
                        if len(spectro_name)<30: spectro_name+=(30-len(spectro_name))*' '
                        else: spectro_name=spectro_name[:30]
                        self.switch_spectro.configure(text=spectro_name)
                        self.switch_spectro.select()
                        self.button_acquire_hyp.configure(state = "normal")
                        self.button_co.configure(state="disabled")
                        self.update()
                except Exception:
                    pass
                

    def spec_disconnection(self):
        self.switch_spectro.configure(text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["functions"]["spec_disconnection"]["switch_spectro"])
        self.switch_spectro.deselect()
        self.button_acquire_hyp.configure(state = "disabled")
 
        if self.acq_config.hardware.spectrometer.DeviceName != '':
            self.acq_config.hardware.spectrometer.spec_close()
            self.switch_spectro.configure(state= "normal")
            self.button_co.configure(text=self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["functions"]["spec_disconnection"]["switch_spectro"],command=self.spec_connection)
        else:
            pass
 
 
    def json_actualisation(self):
        with open(acquisition_json_path, "r") as file:
             acquisition_json_object= json.load(file)

        with open(hardware_json_path, "r") as file:
            hardware_json_object = json.load(file)

        with open(software_json_path, "r") as file:
            software_json_object = json.load(file)
      
        hardware_json_object["name_spectro"] = self.acq_config.hardware.name_spectro
        acquisition_json_object["imaging_method"] = self.methods_optionemenu.get()
        acquisition_json_object["spatial_res"] = int(self.entry_img_res.get())
        
        with open(acquisition_json_path, "w") as file:
            json.dump(acquisition_json_object, file,indent=4)
        
        with open(hardware_json_path, "w") as file:
            json.dump(hardware_json_object, file,indent=4)
        
        with open(software_json_path, "w") as file:
            json.dump(software_json_object, file,indent=4)

 
    def params_actualisation(self):
        self.json_actualisation()
        self.acq_config.hardware.spectrometer.spec_close()
        del self.acq_config
        self.acq_config = Acquisition()
        self.acq_config.hardware.spectrometer.spec_open()
        self.acq_config.hardware.spectrometer.integration_time_ms = self.acq_config.hardware.spectrometer.integration_time_ms
        self.acq_config.hardware.spectrometer.set_integration_time()
        
 
    def thread_acquire_hyp(self):
        self.close_window_proj()
        self.process=threading.Thread(target=self.acquire_hyp)
        self.process.start()
    
    def acquire_hyp(self):
         
        # Entries actualisation
        self.params_actualisation()
        
        self.acq_res=[]
        self.window_size_test()
        self.acq_config.OP_init()
        if self.acq_config.periode_pattern<60 :self.acq_config.periode_pattern=60
            
        while self.acq_config.spectro_flag:
            pass
        self.close_window_proj()
        time.sleep(1)
        # Start acquisition
        self.progressbar.start()
        est_duration=round(1.5*self.acq_config.nb_patterns*self.acq_config.hardware.periode_pattern/(60*1000),2)
        est_end=(datetime.datetime.now()+datetime.timedelta(minutes=round(est_duration))).strftime('%H:%M:%S')
        est_end_label = self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["block 5"]["est_time_label"]
        self.est_time_label.configure(text=f"{est_end_label}{est_end}")
        self.button_acquire_hyp.configure(state='disabled')
        self.acq_config.thread_acquisition()
        self.progressbar.stop()
        self.est_time_label.configure(text=est_end_label)
        self.progressbar.set(value=0)
        
        self.acq_res=Reconstruction(self.acq_config)
        self.acq_res.data_reconstruction()
                
        #if len(self.acq_config.normalised_datacube)!=0:self.acq_res.hyperspectral_image=self.acq_config.normalised_datacube
        if self.acq_config.pattern_method == 'FourierShift':
                self.acq_res.hyperspectral_image = self.acq_res.hyperspectral_image[1:, 1:, :]  # Shift error correction
        
        # Reconstruct a RGB preview of the acquisition
        self.analysis=Analysis(self.acq_res)
        self.acq_res.rgb_image = self.analysis.get_rgb_image(self.acq_res.imaging_method.reconstructed_image,
                                                              self.acq_config.hardware.spectrometer.wavelengths)
        fdate = date.today().strftime('%d_%m_%Y')  # convert the current date in string
        actual_time = time.strftime("%H-%M-%S")  # get the current time    
        self.acq_res.save_reconstructed_image(f'ONE-PIX_app_{fdate}_{actual_time}','./')
        
        # Display RGB image
        self.clear_graph_tab1()

        self.a_acq.imshow(self.acq_res.rgb_image)
        self.a_acq.set_title(self.widgets_text["specific_GUI"]["complete"]["Acquisition_tab"]["functions"]["switch_spat2im_command"]["spat"],color='white')
        self.a_acq.set_axis_on()
        self.canvas.draw_idle()
        
        self.switch_spat2im.configure(state='normal')
        self.switch_spat2im.select()
        self.button_acquire_hyp.configure(state='normal')

# =============================================================================
#         VI's tab functions
# =============================================================================
       
    # =========================================================================
    #     fonctions pour la sauvegarde
    # =========================================================================
    def save_menu(self):
        self.save_options.configure(state = "disabled")
        self.d = ctk.CTkToplevel(self)
        self.d.maxsize(500,400)
        self.d.attributes('-topmost', 'true')
        
        self.chkSave_id.set(1)
        self.save_id_CB = ctk.CTkCheckBox(self.d, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["save_id_CB"], variable = self.chkSave_id)
        self.save_id_CB.grid(column=0, row=0, padx=10, pady=2.5, rowspan =1, columnspan=1,
                                sticky = "w")
        
        self.chkSave_bands.set(0)
        self.save_bands_CB = ctk.CTkCheckBox(self.d, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["save_bands_CB"], variable = self.chkSave_bands)
        self.save_bands_CB.grid(column=2, row=0, padx=10, pady=2.5, rowspan =1, columnspan=1,
                                sticky = "w")

        
        self.id_format = ctk.CTkComboBox(self.d, variable = ("id_np", "id_tif", "id_png"),
                                    values = ["np array", "TIFF", "PNG"],
                                    state = "readonly")
        self.id_format.set("np array") #index de l'élément sélectionné
        self.id_format.grid(column=0, row=1, padx=10, pady=2.5, rowspan =1, columnspan=1,
                                sticky = "w")
        
        self.bands_format = ctk.CTkComboBox(self.d, variable = ("b_np", "b_tif", "b_png"),
                                    values = ["np array", "TIFF", "PNG"],
                                    state = "readonly")
        self.bands_format.set("np array") #index de l'élément sélectionné
        self.bands_format.grid(column=2, row=1, padx=10, pady=2.5, rowspan =1, columnspan=1,
                                sticky = "w")
        
        
        self.save_desc = ctk.CTkLabel(self.d, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["save_desc"])
        self.save_desc.grid(column=0, row=2, padx=10, pady=(10,2.5), rowspan =1, columnspan=1,
                            sticky="w")
        
        self.shown_save_path = ctk.StringVar()
        self.shown_save_path.set(self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["shown_save_path"])
        self.save_path_label = ctk.CTkEntry(self.d, textvariable = self.shown_save_path,
                                           state = 'readonly',width=300,text_color='red')
        self.save_path_label.grid(column=0, row=3, padx=10, pady=(2.5,10), rowspan =1, columnspan=2)

        self.explore_bouton = ctk.CTkButton(self.d, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["explore_bouton"], 
                                 command = lambda : self.get_dir())
        self.explore_bouton.grid(column=2, row=3, padx=10, pady=(2.5,10), rowspan =1, columnspan=1)
        
        self.comment_label = ctk.CTkLabel(self.d, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["comment_label"])
        self.comment_label.grid(column=0, row=4, padx=10, pady=10, rowspan =1, columnspan=1, sticky="w")
        
        self.save_comment.set("")
        self.comment_text = ctk.CTkEntry(self.d, textvariable = self.save_comment,
                                           state = 'normal',width=300)
        self.comment_text.grid(column=1, row=4, padx=10, pady=10, rowspan =1, columnspan=2,
                            sticky="w")
        
        
        
        self.CANCEL_save_bouton = ctk.CTkButton(self.d, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["CANCEL_save_bouton"],
                                            state = "normal", command = lambda :[self.d.destroy(),
                                                                                           self.save_options.configure(state = "normal")])
        self.CANCEL_save_bouton.grid(column=0, row=5, padx=10, pady=10, rowspan =1, columnspan=1)
        
        self.confirm_bouton = ctk.CTkButton(self.d, text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["save_menu"]["confirm_bouton"], state = "disabled",
                                        command = self.check_path)
        self.confirm_bouton.grid(column=2, row=5, padx=10, pady=10, rowspan =1, columnspan=1)
        self.d.protocol("WM_DELETE_WINDOW", lambda :[self.d.destroy(),
                                                        self.save_options.configure(state = "normal")])


    def get_dir(self):
        path = filedialog.askdirectory(parent=self.d,initialdir=os.getcwd())
        if path != "" and path!=(): # because returns a tupple in the first place
            self.confirm_bouton.configure(state = "normal")
            self.shown_save_path.set(path)
            self.save_path_label.configure(text_color="white")
            self.save_path = path
        else:
            self.confirm_bouton.configure(state = "disabled")
            


    def check_path(self):
        # self.save_path = self.save_path_label["text"]
        self.save_confirm.configure(state = "normal")
        self.id_SaveFormat = self.id_format.get()
        self.bands_SaveFormat = self.bands_format.get()
        self.d.destroy()
        self.save_options.configure(state="normal")
        

    def save_data(self):
        today = datetime.datetime.now().strftime('%d_%m_%Y_%H:%M:%S')
        self.save_confirm.configure(state = "disabled")
        self.WIP.configure(text=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["WIP"]["WIP_saving"])
        foldername='ONE-PIX_VI_'+self.IM["folder_name"]
        path = self.save_path+"/"+foldername
        if not(os.path.exists(path)):
            os.mkdir(path)
        path += "/"+today
        os.mkdir(path)
            
        # saving the spectral indices
        if self.chkSave_id.get():
            if self.id_SaveFormat == "PNG":
                os.mkdir(path+"/VI")
                for i in range(len(self.IDXS['names'])):
                    temp_im = self.IDXS['id'][i]
                    temp_im = temp_im + abs(temp_im.min())
                    temp_im = 255 * (temp_im - temp_im.min())/(temp_im.max() - temp_im.min())
                    
                    
                    cv2.imwrite(path+"/VI/"+self.IDXS['names'][i] + ".png", 
                                np.uint8(temp_im))
            
            else:
                im = []
                for i in range(len(self.IDXS['names'])):
                    im.append(self.IDXS['id'][i].reshape(-1))
                np.save(path+"/"+"indices_names", np.asarray(self.IDXS['names']))
                if self.id_SaveFormat == "np array":
                    np.save(path+"/"+"VI", np.asarray(im))
                    
                elif self.id_SaveFormat == "TIFF":
                    tiff.imsave(path+"/"+"indices.tiff",
                               np.asarray([np.uint8(255*(i-i.min())/(i.max()-i.min())) for i in self.IDXS['id']]))
        # saving the bands
        if self.chkSave_bands.get():
            if self.bands_SaveFormat == "PNG":
                os.mkdir(path+"/bands")
                for i in range(len(self.IM['bands_names'])):
                    temp_im = self.IM['bands'][i]
                    temp_im = temp_im + abs(temp_im.min())
                    temp_im = 255 * (temp_im - temp_im.min())/(temp_im.max() - temp_im.min())
                
                    cv2.imwrite(path+"/bands/"+self.IM['bands_names'][i] + ".png", 
                                np.uint8(temp_im))
            
            else:
                im = []
                for i in range(len(self.IM['bands_names'])):
                    im.append(self.IM['bands'][i].reshape(-1))
                np.save(path+"/"+"bands_names", np.asarray(self.IM['bands_names']))
                if self.id_SaveFormat == "np array":
                    np.save(path+"/"+"bands", np.asarray(im))
                    
                elif self.id_SaveFormat == "TIFF":
                    tiff.imsave(path+"/"+"bands.tiff", np.asarray(self.IM['shown_bands']))
        
        # creation of the log file
        with open(path+"/"+"log.txt", "w") as f:
            print("version : alpha-2023_02_16", file = f)
            print("satellite name : " + self.sat_path.split('/')[-1][:-4], file = f)
            print("original data file : " + self.IM["folder_name"], file = f)
            print("chosen domain : " + self.domain.get(), file = f)
            if self.sort_choice.get() =="keep all":
                print("filtering method : " + "None", file = f)
            else:
                print("filtering method : " + "max-"+self.critere.get(), file = f)
            if self.chkSave_id.get():
                print("number of kept Spectral Indices : " + str(len(self.IDXS["names"])), file = f)
                print("chosen format for indices : " + self.id_SaveFormat, file = f)
            else:
                print("number of kept Spectral Indices : " + "0", file = f)
                print("chosen format for indices : " + "None", file = f)
                
            if self.chkSave_bands.get():
                print("chosen format for bands : " + self.bands_SaveFormat, file = f)
            else:
                print("chosen format for bands : " + "None", file = f)
            print("comment : " + self.save_comment.get(), file = f)
        self.save_options.configure(state = "normal")
        self.WIP.configure(text = "Done")
        

    # =========================================================================
    #     pour le bind des combobox des indices et des bandes
    # =========================================================================
    def get_combobox_value(self, sel):
        if sel=="idx":
            try:
                self.shown_IDX = self.indice_list.get()
                self.indices_scale.set(self.IDXS["names"].index(self.shown_IDX))
            except ValueError:
                warning_text = self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["get_combobox_value"]["warning_VI"]
                showwarning(warning_text[0],warning_text[1])
                self.indice_scale.set(self.IDXS["names"][0])
        elif sel=="bands":
            try:
                self.shown_band = self.bands_list.get()
                self.bands_scale.set(self.IM["bands_names"].index(self.shown_band))
            except ValueError:
                warning_text = self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["functions"]["get_combobox_value"]["warning_bands"]
                showwarning(warning_text[0],warning_text[1])
                self.bands_scale.set(self.IM["bands_names"][0])
        self.update()
            
        

    # =========================================================================
    #     griser sur selection dans la combobox
    # =========================================================================
    def get_mode_choice(self):
        filter_list = self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["sort_choice"]
        if filter_list.index(self.sort_choice.get())==0: # if self.sort_choice.get()=="keep all"
            self.critere.configure(state = "disabled")
            self.nb_keep.configure(state = "disabled")
        elif filter_list.index(self.sort_choice.get())==1: # if self.sort_choice.get()=="simple filter"
            self.critere.configure(state = "normal")
            self.nb_keep.configure(state = "normal")
            self.nb_keep.delete(0,tk.END)
            self.nb_keep.insert(0,"10")
        
        
        
    # =========================================================================
    #     demande des chemins pour le calcul
    # =========================================================================
    def get_path(self, name = None):
       
        if name =="sat":
            path = filedialog.askopenfilename(initialdir=os.getcwd())
            if path.endswith(".csv"):
                self.sat_path_label.configure(text_color='white')
                self.shown_sat_path.set(os.path.join('', *path.split('/')[-3:]))
                self.sat_path=path
            else:
                self.sat_path_label.configure(text_color='red')
                self.shown_sat_path.set(os.path.join('', *path.split('/')[-3:]))
                self.calc_bouton.configure(state = "disabled")
            
        else: #if name == "data"
            self.folder_path=filedialog.askdirectory(initialdir='../Hypercubes')
            data_list=glob.glob(self.folder_path+'/*.hdr')+glob.glob(self.folder_path+'/*.tif')
            if data_list[0].endswith((".tif",".hdr")):
                self.data_path_label.configure(text_color='white')
                self.shown_data_path.set(os.path.join('', *data_list[0].split('/')[-3:]))
                self.data_path=data_list[0]
            else:
                self.data_path_label.configure(text_color='red')
                self.shown_data_path.set(os.path.join('', *data_list[0].split('/')[-3:]))
                self.calc_bouton.configure(state = "disabled")

        if (self.sat_path.endswith(".csv") and self.data_path.endswith((".tif",".hdr"))):
            self.calc_bouton.configure(state = "normal")

            

    def plot_indices(self, val):
            VAL = int(val)
            self.a.clear()
            self.a.axis('off')
            current_cmap = CM.get_cmap()
            current_cmap.set_bad(color='white')
            self.a.set_title(self.IDXS["names"][VAL],color='white')
            self.color.clear()
            shw = self.a.imshow((self.IDXS["id"][VAL]))
            self.f.colorbar(shw, cax = self.color)
            self.color.ticklabel_format(useOffset=False)
            self.f.canvas.draw_idle()
            self.indices_scale.configure(label = self.IDXS["names"][VAL])
            self.indice_list.current(VAL)
            
    def plot_bands(self, val):
            VAL = int(val)
            self.bands_subplot.axis('off')
            self.bands_subplot.clear()
            self.bands_subplot.axis('off')
            self.bands_subplot.set_title(self.IM["bands_names"][VAL],color='white')
            shw = self.bands_subplot.imshow((self.IM["shown_bands"][VAL]))
            self.bands_graph.canvas.draw_idle()
            self.bands_scale.configure(label = self.IM["bands_names"][VAL])
            self.bands_list.current(VAL)


    def calculation(self):
        self.indices_scale.configure(state = "disabled")
        self.indice_list.configure(state = "disabled")
        
        self.bands_scale.configure(state = "disabled")
        self.bands_list.configure(state = "disabled")
        
        self.save_options.configure(state = "disabled")
        self.WIP.configure(text = "Computing...")
#         self.update()
        trad_SIDomain=self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 2"]["domain"]
        domain_list=["vegetation","snow","water"]
        domain = domain_list[trad_SIDomain.index(self.domain.get())]
        id_names = [n for n in sp.indices if (sp.indices[n].application_domain==domain)]
        self.get_idx(id_names)
        # for i in range(len(id_names)):
        #     indice = self.IDXS["id"][i]
        #     self.IDXS["id"][i] = indice/np.max(abs(indice))
        self.sort_idx()
        # tri des indices dans l'ordre alphabétique (majuscules exclues) pour isoler le code
        any, self.IDXS["names"], self.IDXS["id"] = zip(*sorted(
            zip([name.lower() for name in self.IDXS["names"]],
                self.IDXS["names"], self.IDXS["id"])))
        
        # tri des bandes dans l'ordre alphabétique (majuscules exclues) pour isoler le code
        any, self.IM["bands_names"], self.IM["shown_bands"] = zip(*sorted(
            zip([name.lower() for name in self.IM["bands_names"]],
                self.IM["bands_names"], self.IM["shown_bands"])))
        
        self.WIP.configure(text = "Done")
        self.indices_scale.configure(state = "normal", to_ = len(self.IDXS["names"]) - 1,
                              label = self.IDXS["names"][0])
        self.bands_scale.configure(state = "normal", to_ = len(self.IM["bands_names"]) - 1,
                              label = self.IM["bands_names"][0])
        self.indices_scale.set(0) #after the state = activate to provide refresh the label
        self.bands_scale.set(0)
        
        self.plot_indices(self.indices_scale.get())
        self.plot_bands(self.bands_scale.get())
        
        self.indice_list.configure(state = "normal")
        self.save_options.configure(state = "normal")
        self.bands_list.configure(state = "normal")
        
        
        self.indice_list.set_completion_list(self.IDXS["names"])
        self.bands_list.set_completion_list(self.IM["bands_names"])
        self.indice_list.current(0)
        self.bands_list.current(0)
        self.update()

    # =============================================================================
    #         fonctions de réduction du nombre d'indices affichés
    # =============================================================================
    def sort_idx(self):
        # filtering "only background" and outliers
        temp = {"id":[], "names":[]}
        for i in range(len(self.IDXS["names"])):
            if len(np.unique(self.IDXS["id"][i]))!=1:
                temp["id"].append(self.IDXS["id"][i])
                temp["names"].append(self.IDXS["names"][i])
        temp["id"] = np.asarray(temp["id"])
        self.IDXS = temp
        
        filters_list = self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["sort_choice"]
        cur_filter = filters_list.index(self.sort_choice.get())
        if cur_filter == 1: # if current filter is "simple filter"
            nb = int(self.nb_keep.get())
            if nb>len(self.IDXS["names"]):
                nb = len(self.IDXS["names"])
                
            # entropy of the image (without nans and outliers)
            critere_list = self.widgets_text["specific_GUI"]["complete"]["VI_tab"]["block 4"]["critere"]
            cur_critere = critere_list.index(self.critere.get())
            if cur_critere == 1: # if current critere is "Entropy"
                ENTR = []
                for i in range(len(self.IDXS["names"])):
                    im = self.IDXS["id"][i]
                    im = im[~np.isnan(im)]
                    im[im>np.quantile(im,q = .95)]=np.nan
                    im[im<np.quantile(im,q = .05)]=np.nan
                    im = im[~np.isnan(im)]
                    ENTR.append(np.var(im))
                names = self.IDXS["names"]
                ids = self.IDXS["id"] #no need to set it as a list, sort will do
                ENTR, names, ids = zip(*sorted(zip(ENTR, names, ids), reverse=True))
                self.IDXS = {"id": np.asarray(ids[:nb]),
                        "names": names[:nb]}
                
            # variance of the image (without nans and outliers)
            if cur_critere == 0: # if current critere is "Variance"
                VAR = []
                for i in range(len(self.IDXS["names"])):
                    im = self.IDXS["id"][i]
                    im = im[~np.isnan(im)]
                    im[im>np.quantile(im,q = .95)]=np.nan
                    im[im<np.quantile(im,q = .05)]=np.nan
                    im = im[~np.isnan(im)]
                    VAR.append(np.var(im))
                names = self.IDXS["names"]
                ids = self.IDXS["id"] #no need to set it as a list, sort will do
                VAR, names, ids = zip(*sorted(zip(VAR, names, ids), reverse=True))
                self.IDXS = {"id": np.asarray(ids[:nb]),
                        "names": names[:nb]}


        
    def get_idx(self, idx_to_compute, C1 = sp.constants.C1.default,
                C2 = sp.constants.C2.default,
                L = sp.constants.L.default,
                PAR = 450, #450 ou 650 selon la chlorophyle étudiée
                alpha = sp.constants.alpha.default,
                beta = sp.constants.beta.default,
                c = sp.constants.c.default,
                cexp = sp.constants.cexp.default,
                fdelta = sp.constants.fdelta.default,
                g = sp.constants.g.default,
                gamma = sp.constants.gamma.default,
                k = sp.constants.k.default,
                lambdaG = 507,
                lambdaN = 1000,
                lambdaR = 680,
                nexp = sp.constants.nexp.default,
                omega = sp.constants.omega.default,
                p = sp.constants.p.default,
                sigma = sp.constants.sigma.default,
                sla = sp.constants.sla.default,
                slb = sp.constants.slb.default):
        df = pd.read_csv(self.sat_path, delimiter=';', engine = 'c')
        df2=df.dropna(axis = 0, how = 'all').dropna(axis = 1, how = 'all')
        
        if self.data_path.endswith('.tif') or self.data_path.endswith('.tiff'):
            self.IM = {"IM" : tiff.imread(self.data_path),
                        "wl" : np.load([f for f in os.listdir(os.chdir(os.path.dirname(self.data_path)))
                                        if f.startswith("wavelengths")][0]),
                        "folder_name" : self.data_path.split('/')[-2][:]}
        
        elif self.data_path.endswith('.hdr'):
            self.analysis=Analysis(rec=None,data_path=self.folder_path)
            res=self.analysis.imaging_method.image_analysis_method.data_dict
            self.IM = {"IM" : res["hyperspectral_image"].T,
                        "wl" : res["wavelengths"],
                        "folder_name" : self.data_path.split('/')[-2][:]}
        
        bands = []
        f = []
        for i in range(1,len(df2.columns)):
            f.append(interpolate.interp1d(df2['WL'], df2[df2.columns[i]])(self.IM["wl"]))
            bands.append((self.IM["IM"]*(f[i-1].reshape(-1,1,1))).sum(axis = 0))
        bands = np.asarray(bands).swapaxes(1,2)
        
        self.IM["bands"] = bands #ajout des bandes spectrales dans le dictionnaire
        self.IM["shown_bands"] = [np.uint8(255*(i-i.min())/(i.max()-i.min())) for i in self.IM["bands"]]
        
        self.IM["bands_names"] = ["Aerosols", "Blue", "Green", "Red",
                          "Red Edge 1", "Red Edge 2", "Red Edge 3",
                          "NIR", "NIR 2", "Water Vapour", "SWIR 1",
                          "SWIR 2"]
        
        A,B,G,R,RE1,RE2,RE3,N,N2,WV,any,S1,S2 = list(bands[np.arange(13),:,:])
        bands = np.array([A,B,G,R,RE1,RE2,RE3,N,N2,WV,S1,S2])
        
        
        da = xr.DataArray(
            bands,
            dims = ("band","x","y"),
            coords = {"band":self.IM["bands_names"]}
            )
        
        idx = sp.computeIndex(
            index = [f for f in idx_to_compute if not('G1' in sp.indices[f].bands)],
            A = da.sel(band = "Aerosols"),
            B = da.sel(band = "Blue"),
            G = da.sel(band = "Green"),
            R = da.sel(band = "Red"),
            RE1 = da.sel(band = "Red Edge 1"),
            RE2 = da.sel(band = "Red Edge 2"),
            RE3 = da.sel(band = "Red Edge 3"),
            N = da.sel(band = "NIR"),
            N2 = da.sel(band = "NIR 2"),
            WV = da.sel(band = "Water Vapour"),
            S1 = da.sel(band = "SWIR 1"),
            S2 = da.sel(band = "SWIR 2"),
            C1 = C1,
            C2 = C2,
            L = L,
            PAR = PAR,
            alpha = alpha,
            beta = beta,
            c = c,
            cexp = cexp,
            fdelta = fdelta,
            g = g,
            gamma = gamma,
            k = k,
            lambdaG = lambdaG,
            lambdaN = lambdaN,
            lambdaR = lambdaR,
            nexp = nexp,
            omega = omega,
            p = p,
            sigma = sigma,
            sla = sla,
            slb = slb
            )
        self.IDXS = {"id":np.asarray(idx),"names":list(np.asarray(idx.index))}
        
          
            
    def open_languageConfig(self):
        with open("languages/config.json", 'r') as f:
            lang_conf = json.load(f)
          
        lang_list = lang_conf['installed_language']
        jsonFile = list(lang_list)[list(lang_list.values()).index(lang_conf["last_choice"])]
        print(jsonFile)
        
        with open(f"languages/{jsonFile}.json", 'r') as f:
            self.widgets_text = json.load(f)
            

class Toolbar(NavigationToolbar2Tk):
    def set_message(self, s):
        pass

class AutocompleteCombobox(ttk.Combobox):
    """
    :class:`ttk.Combobox` widget that features autocompletion.
    """
    def __init__(self, master=None, completevalues=None, **kwargs):
        """
        Create an AutocompleteCombobox.
        
        :param master: master widget
        :type master: widget
        :param completevalues: autocompletion values
        :type completevalues: list
        :param kwargs: keyword arguments passed to the :class:`ttk.Combobox` initializer
        """
        ttk.Combobox.__init__(self, master, values=completevalues, **kwargs)
        self._completion_list = completevalues
        if isinstance(completevalues, list):
            self.set_completion_list(completevalues)
        self._hits = []
        self._hit_index = 0
        self.position = 0     
        

    def set_completion_list(self, completion_list):
        """
        Use the completion list as drop down selection menu, arrows move through menu.
        
        :param completion_list: completion values
        :type completion_list: list
        """
        self._completion_list = sorted(completion_list, key=str.lower)  # Work with a sorted list
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        self.configure(values = self._completion_list)  # Setup our popup menu


    def autocomplete(self, delta=0):
        """
        Autocomplete the Combobox.
        
        :param delta: 0, 1 or -1: how to cycle through possible hits
        :type delta: int
        """
        if delta:  # need to delete selection otherwise we would fix the current position
            self.delete(self.position, tk.END)
        else:  # set position to end so selection starts where textentry ended
            self.position = len(self.get())
        # collect hits
        _hits = []
        for element in self._completion_list:
            if element.lower().startswith(self.get().lower()):  # Match case insensitively
                _hits.append(element)
        # if we have a new hit list, keep this in mind
        if _hits != self._hits:
            self._hit_index = 0
            self._hits = _hits
        # only allow cycling if we are in a known hit list
        if _hits == self._hits and self._hits:
            self._hit_index = (self._hit_index + delta) % len(self._hits)
        # now finally perform the auto completion
        if self._hits:
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, tk.END)


    def handle_keyrelease(self, event):
        """
        Event handler for the keyrelease event on this widget.
        
        :param event: Tkinter event
        """
        if event.keysym == "BackSpace":
            self.delete(self.index(tk.INSERT), tk.END)
            self.position = self.index(tk.END)
        if event.keysym == "Left":
            if self.position < self.index(tk.END):  # delete the selection
                self.delete(self.position, tk.END)
            else:
                self.position -= 1  # delete one character
                self.delete(self.position, tk.END)
        if event.keysym == "Right":
            self.position = self.index(tk.END)  # go to end (no selection)
        if event.keysym == "Return":
            self.handle_return(None)
            return
        if len(event.keysym) == 1:
            self.autocomplete()


    def handle_return(self, event):
        """
        Function to bind to the Enter/Return key so if Enter is pressed the selection is cleared
        
        :param event: Tkinter event
        """
        self.icursor(tk.END)
        self.selection_clear()

if __name__ == "__main__":
    app = OPApp()
    app.protocol("WM_DELETE_WINDOW", partial(app.close_window))
    app.mainloop()
