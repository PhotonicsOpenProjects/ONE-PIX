# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 11:57:31 2023

HUB interfaces ONE-PIX

@author: brechl
"""
import sys
import os
sys.path.append(os.path.abspath('./ONE-PIX_soft/src'))
sys.path.append(os.path.abspath('./ONE-PIX_soft'))

import tkinter as tk
import customtkinter as ctk
from tkinter import  ttk
from tkinter.messagebox import showwarning
from PIL import Image
from AcquisitionConfig import is_raspberrypi
from matplotlib.backends.backend_tkagg import  NavigationToolbar2Tk

import json

import os
import screeninfo
path_to_GUI = '/'.join([os.getcwd(),'ONE-PIX_soft/GUI'])
os.chdir(path_to_GUI)
class OPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.monitor_sz=screeninfo.get_monitors()[0]
        self.open_languageConfig()
        self.update_trad()
        self.generate_GUI()
        self.isNormalized = False
        self.acquisition_method = None
        
        # self.GUI_mode=None
        
    def generate_GUI(self):
        self.title('ONE-PIX APP')
        width=680
        height=250
        x = (self.monitor_sz.width -width)//2-100
        y = (self.monitor_sz.height-height)//2-100
        if is_raspberrypi(): x,y=x+100,y+100
        self.geometry('%dx%d+%d+%d' % (width, height, x, y))
        self.logo_image = ctk.CTkImage(Image.open(path_to_GUI + "/logo_ONE-PIX.png"),
                                               size=(200, 200))
        self.logo_image_label = ctk.CTkLabel(self, image=self.logo_image,text="")
        self.logo_image_label.grid(row=0, column=0,sticky='nsew',pady=20,padx=(10,10))    

        
        self.Hub_frame = ctk.CTkFrame(self,corner_radius=15)
        self.Hub_frame.grid(row=0, column=1, pady=25, padx = (5,5), rowspan=1, columnspan=1, sticky="nsew")
        
        self.GuiMode_choice = ctk.CTkComboBox(self.Hub_frame, values = self.GuiMode_choice_text,
                                    state = "readonly")
        self.GuiMode_choice.set(self.GuiMode_choice_text[0]) #index de l'élément sélectionné
        self.GuiMode_choice.grid(column=0, row=0, pady=(10,2.5), padx = (0,0))
        
        self.choseLanguage = ttk.Combobox(self.Hub_frame, textvariable = self.lang_names,
                                   state = "readonly", values = self.lang_values,font=('Helvetica', 13),width=15)
        self.choseLanguage.current(self.lang_values.index(self.curLanguage)) #index de l'élément sélectionné
        self.choseLanguage.grid(column=1, row=0, pady=(10,2.5), padx = (0,0))
        self.choseLanguage.bind("<<ComboboxSelected>>", lambda event=None:
                        self.change_language())
                
        self.Gui_help = ctk.CTkButton(self.Hub_frame, text=" ?", font=('Helvetica', 15, 'bold'), width =12, command=self.open_Gui_help)
        
        self.Gui_help.grid(column=2, row=0, pady=(10,2.5), padx = (1,3))
        
        self.CompleteAcquisition_button = ctk.CTkButton(self.Hub_frame, text = self.CompleteAcquisition_button_text,
                                                   fg_color = "#3B8ED0", hover_color="#36719F",height=40,
                                                   command = self.CompleteLaunching, font=('Helvetica', 15, 'bold'))
        self.CompleteAcquisition_button.grid(row=2, column=0, sticky="news",pady=(30,2.5), padx = (35,15))
        self.AddressedAcquisition_button = ctk.CTkButton(self.Hub_frame, text = self.AddressedAcquisition_button_text,
                                                    fg_color = "#3B8ED0", hover_color="#36719F",height=40,
                                                    command = self.AddressedLaunching, font=('Helvetica', 15, 'bold'))
        self.AddressedAcquisition_button.grid(row=2, column=1, pady=(30,2.5), padx = (2.5,2.5),sticky="news")
        
        
        self.Exit_button = ctk.CTkButton(self.Hub_frame, text = self.Exit_button_text, fg_color = "#D70000", hover_color="#9D0000",
                                    command = self.close_window,height=40)
        self.Exit_button.grid(row=3, column=0, pady=(25,2.5), padx = (25,2.5),columnspan=2)

    def CompleteLaunching(self):
        self.acquisition_method = 'Complete'
        self.normalization_request()

    def AddressedLaunching(self):
        self.acquisition_method = 'Addressed'
        self.normalization_request()
        
    def normalization_request(self):
        self.pop_up = ctk.CTkToplevel()
        width=350
        height=150
        x = (self.monitor_sz.width/2) - (width/2)
        y = (self.monitor_sz.height/2) - (height/2)
        self.pop_up.geometry('%dx%d+%d+%d' % (width, height, x, y))
        self.pop_up.attributes('-topmost', 1)
        self.pop_upText = ctk.CTkLabel(self.pop_up, text = self.normalization_request_pop_upText, width=300,
                               height=100, corner_radius=10, wraplength=300, font=('Helvetica', 18, 'bold'))
        self.pop_upText.grid(row=0, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=2, sticky="news")
        self.normalize_yesButton = ctk.CTkButton(self.pop_up, text = self.normalization_request_normalize_yesButton, fg_color = '#31D900', hover_color="#249F00", command = self.normalisation_specifications)
        self.normalize_yesButton.grid(row=1, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky="news")
        
        self.normalize_noButton = ctk.CTkButton(self.pop_up, text = self.normalization_request_normalize_noButton, fg_color = '#D70000', hover_color="#9D0000", command = self.deactivate_normalization)
        self.normalize_noButton.grid(row=1, column=1, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky="news")
        self.normalizationHelp_button = ctk.CTkButton(self.pop_up, text="?", font=('Helvetica', 18, 'bold'), width =12, command=self.open_normalizeation_help)
        self.normalizationHelp_button.grid(row=0, column = 2, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky="")
    def normalisation_specifications(self):
        print(self.GuiMode_choice.get())
        self.pop_upText.configure(text = self.normalisation_specifications_pop_upText)
        self.normalize_yesButton.configure(text = self.normalisation_specifications_normalize_yesButton, command = self.activate_normalisation)
        self.normalize_noButton.configure(text = self.normalisation_specifications_normalize_noButton, command = lambda:self.pop_up.destroy())
    
    def deactivate_normalization(self):
        self.isNormalized = False
        self.launch_GUI()
            
    def activate_normalisation(self):
        self.isNormalized = True
        self.launch_GUI()

    def open_Gui_help(self):
        self.guiHelp_top = ctk.CTkToplevel()
        self.guiHelp_top.attributes('-topmost', 1)
        width=425
        height=425
        x = (self.monitor_sz.width/2) - (width/2)
        y = (self.monitor_sz.height/2) - (height/2)
        self.guiHelp_top.geometry('%dx%d+%d+%d' % (width, height, x, y))
        self.guiHelp_frame = ctk.CTkScrollableFrame(self.guiHelp_top, width = 400, height = 400)
        self.guiHelp_frame.grid(row = 0, column=0)
    
        self.acquisitionHelp_title = ctk.CTkLabel(self.guiHelp_frame, text = self.acquisitionHelp_title_text, font=('Helvetica', 18, 'bold'))
        self.acquisitionHelp_title.grid(row=0, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
        self.acquisitionHelp = ctk.CTkLabel(self.guiHelp_frame, text = self.acquisitionHelp_text, wraplength = 395, justify = 'left')
        self.acquisitionHelp.grid(row=1, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        
        self.modeHelp_title = ctk.CTkLabel(self.guiHelp_frame, text = self.modeHelp_title_text, font=('Helvetica', 18, 'bold'))
        self.modeHelp_title.grid(row=2, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
        
        self.modeDescription = ctk.CTkLabel(self.guiHelp_frame, text = self.modeDescription_text, wraplength = 395, justify="left")
        self.modeDescription.grid(row=3, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
        
        self.modeHelpSimple_title = ctk.CTkLabel(self.guiHelp_frame, text = self.modeHelpSimple_title_text, font=('Helvetica', 15, 'bold'))
        self.modeHelpSimple_title.grid(row=4, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
        
        self.modeHelpSimpleFull_title = ctk.CTkLabel(self.guiHelp_frame, text = self.modeHelpSimpleFull_title_text, font=('Helvetica', 12, 'bold'))
        self.modeHelpSimpleFull_title.grid(row=5, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.modeSimpleFullDescription = ctk.CTkLabel(self.guiHelp_frame, text = self.modeSimpleFullDescription_text, wraplength = 395, justify="left")
        self.modeSimpleFullDescription.grid(row=6, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.modeHelpSimpleAddressed_title = ctk.CTkLabel(self.guiHelp_frame, text = self.modeHelpSimpleAddressed_title_text, font=('Helvetica', 12, 'bold'))
        self.modeHelpSimpleAddressed_title.grid(row=7, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.modeSimpleAddressedDescription = ctk.CTkLabel(self.guiHelp_frame, text = self.modeSimpleAddressedDescription_text, wraplength = 395, justify="left")
        self.modeSimpleAddressedDescription.grid(row=8, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        
        
        self.modeHelpAdvanced_title = ctk.CTkLabel(self.guiHelp_frame, text = self.modeHelpAdvanced_title_text, font=('Helvetica', 15, 'bold'))
        self.modeHelpAdvanced_title.grid(row=9, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
        
        self.modeHelpAdvancedFull_title = ctk.CTkLabel(self.guiHelp_frame, text = self.modeHelpAdvancedFull_title_text, font=('Helvetica', 12, 'bold'))
        self.modeHelpAdvancedFull_title.grid(row=10, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.modeAdvancedFullDescription = ctk.CTkLabel(self.guiHelp_frame, text = self.modeAdvancedFullDescription_text, wraplength = 395, justify="left")
        self.modeAdvancedFullDescription.grid(row=11, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.modeHelpAdvancedAddressed_title = ctk.CTkLabel(self.guiHelp_frame, text = self.modeHelpAdvancedAddressed_title_text, font=('Helvetica', 12, 'bold'))
        self.modeHelpAdvancedAddressed_title.grid(row=12, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        self.modeAdvancedAddressedDescription = ctk.CTkLabel(self.guiHelp_frame, text = self.modeAdvancedAddressedDescription_text, wraplength = 395, justify="left")
        self.modeAdvancedAddressedDescription.grid(row=13, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='w')
        
            
        
    def open_normalizeation_help(self):
        self.normalizationHelp_top = ctk.CTkToplevel()
        self.pop_up.attributes('-topmost', 0)
        self.normalizationHelp_top.attributes('-topmost', 1)
        self.normalizationHelp_frame = ctk.CTkScrollableFrame(self.normalizationHelp_top, width = 400, height = 400)
        self.normalizationHelp_frame.grid(row=0, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
        self.normalizationHelp_title = ctk.CTkLabel(self.normalizationHelp_frame, text = self.normalizationHelp_title_text, font=('Helvetica', 18, 'bold'))
        self.normalizationHelp_title.grid(row=0, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
        # f = open('help_texts.json')
        # text_dict = json.load(f)
        # f.close()
        self.normalizationHelp = ctk.CTkLabel(self.normalizationHelp_frame, text = self.normalizationHelp_text, wraplength = 395, justify = 'left')
        self.normalizationHelp.grid(row=1, column=0, pady=(2.5,2.5), padx = (2.5,2.5), rowspan=1, columnspan=1, sticky='')
    
    def close_window(self):
        #plt.close('all')
        self.quit()
        self.destroy()
        
    def launch_GUI(self):
        path_to_json = '/'.join(['/'.join(path_to_GUI.split('/')[:-1]), 'acquisition_param_ONEPIX.json'])
        print(path_to_json)
        f = open(path_to_json)
        acq_params = json.load(f)
        f.close()
        acq_params["mode_choice"]=self.GuiMode_choice.get()
        acq_params["acquisition_method"]=self.acquisition_method
        acq_params["Normalisation"]=self.isNormalized
        with open(path_to_json, 'w') as outfile:
            json.dump(acq_params, outfile)
            outfile.close()
            
        with open("languages/config.json", 'r') as f:
            lang = json.load(f)
            f.close()
            lang["last_choice"] = self.curLanguage
        with open("languages/config.json", 'w') as f:    
            json.dump(lang, f)
            f.close()
            
        if self.GuiMode_choice.get()==self.GuiMode_choice_text[0]: # if simple
            if self.acquisition_method=='Complete':
                if self.isNormalized:
                    self.destroy()
                    os.system("python ../src/getReference.py")
                    os.system("python modif_simple.py")
                else:
                    self.destroy()
                    os.system("python modif_simple.py")
                    
            elif self.acquisition_method=='Addressed':
                if self.isNormalized:
                    self.destroy()
                    os.system("python ../src/getReference.py")
                    os.system("python simple_addressed_APP.py")
                else:
                    self.destroy()
                    os.system("python simple_addressed_APP.py")
                    
        elif self.GuiMode_choice.get()==self.GuiMode_choice_text[1]: # if advanced
            if self.acquisition_method=='Complete':
                if self.isNormalized:
                    self.destroy()
                    os.system("python ../src/getReference.py")
                    os.system("python ONEPIX_app.py")
                else:
                    self.destroy()
                    os.system("python ONEPIX_app.py")
            elif self.acquisition_method=='Addressed':
                if self.isNormalized:
                    self.destroy()
                    os.system("python ../src/getReference.py")
                    os.system("python addressed_APP.py")
                else:
                    self.destroy()
                    os.system("python addressed_APP.py")
    
    def open_languageConfig(self):
        f = open('./languages/config.json')
        lang_dict = json.load(f)
        f.close()
        self.curLanguage = lang_dict["last_choice"] #current long_name
        # self.curLanguage = list(lang_dictapp.L)[list(lang_dict.values()).index(lang_dict["last_choice"])] #current short name
        self.lang_list = lang_dict["installed_language"]
        self.lang = list(self.lang_list)[list(self.lang_list.values()).index(self.curLanguage)] # current short name given the long
        self.lang_names = list(self.lang_list.keys()) #list of the short names
        self.lang_values = list(self.lang_list.values()) #list of the long names
        
    def change_language(self):
        self.curLanguage = self.choseLanguage.get()
        print(self.curLanguage)
        self.lang = list(self.lang_list)[list(self.lang_list.values()).index(self.curLanguage)]
        print(self.lang)
        self.update_trad()
        self.generate_GUI()
        
    def update_trad(self):
        json_file = '/'.join(["./languages","".join([self.lang,".json"])])
        print(os.path.abspath(os.curdir))
        print(json_file)
        f = open(json_file)
        text = json.load(f)
# =============================================================================
#         buttons
# =============================================================================
        self.GuiMode_choice_text = text["HUB"]["buttons"]["GuiMode_choice"]
        self.CompleteAcquisition_button_text = text["HUB"]["buttons"]["CompleteAcquisition_button"]
        self.AddressedAcquisition_button_text = text["HUB"]["buttons"]["AddressedAcquisition_button"]
        self.Exit_button_text = text["HUB"]["buttons"]["Exit_button"]
        
# =============================================================================
#         functions
# =============================================================================
        self.normalization_request_pop_upText = text["HUB"]["functions"]["normalization_request"]["pop_upText"]
        self.normalization_request_normalize_noButton = text["HUB"]["functions"]["normalization_request"]["normalize_noButton"]
        self.normalization_request_normalize_yesButton = text["HUB"]["functions"]["normalization_request"]["normalize_yesButton"]
        
        self.normalisation_specifications_pop_upText = text["HUB"]["functions"]["normalisation_specifications"]["pop_upText"]
        self.normalisation_specifications_normalize_noButton = text["HUB"]["functions"]["normalisation_specifications"]["normalize_noButton"]
        self.normalisation_specifications_normalize_yesButton = text["HUB"]["functions"]["normalisation_specifications"]["normalize_yesButton"]
        
# =============================================================================
#         help fields
# =============================================================================
        self.acquisitionHelp_title_text = text["HUB"]["help"]["acquisition"]["title"]
        self.acquisitionHelp_text = text["HUB"]["help"]["acquisition"]["corpse"]
        self.modeHelp_title_text = text["HUB"]["help"]["mode"]["title"]
        self.modeDescription_text = text["HUB"]["help"]["mode"]["description"]
        self.modeHelpSimple_title_text = text["HUB"]["help"]["mode"]["simple_mode"]["title"]
        self.modeHelpSimpleFull_title_text = text["HUB"]["help"]["mode"]["simple_mode"]["full"]["title"]
        self.modeSimpleFullDescription_text = text["HUB"]["help"]["mode"]["simple_mode"]["full"]["description"]
        self.modeHelpSimpleAddressed_title_text = text["HUB"]["help"]["mode"]["simple_mode"]["addressed"]["title"]
        self.modeSimpleAddressedDescription_text = text["HUB"]["help"]["mode"]["simple_mode"]["addressed"]["description"]
        self.modeHelpAdvanced_title_text = text["HUB"]["help"]["mode"]["advanced_mode"]["title"]
        self.modeHelpAdvancedFull_title_text = text["HUB"]["help"]["mode"]["advanced_mode"]["full"]["title"]
        self.modeAdvancedFullDescription_text = text["HUB"]["help"]["mode"]["advanced_mode"]["full"]["description"]
        self.modeHelpAdvancedAddressed_title_text = text["HUB"]["help"]["mode"]["advanced_mode"]["addressed"]["title"]
        self.modeAdvancedAddressedDescription_text = text["HUB"]["help"]["mode"]["advanced_mode"]["addressed"]["description"]
        self.normalizationHelp_title_text = text["HUB"]["help"]["normalization"]["title"]
        self.normalizationHelp_text = text["HUB"]["help"]["normalization"]["corpse"]
        
        
if __name__ == "__main__":
    app = OPApp()
    app.protocol("WM_DELETE_WINDOW", app.close_window)
    app.mainloop()