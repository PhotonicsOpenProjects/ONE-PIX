import os
import numpy as np
import matplotlib.pyplot as plt
import xarray as xr
import pandas as pd
import spyndex as sp
import tifffile as tiff
import cv2

from scipy import interpolate
import json
from decimal import Decimal

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from skimage.measure import shannon_entropy as entropy

#%% classe de combobox autocomplete

tk_umlauts = ['odiaeresis', 'adiaeresis', 'udiaeresis', 'Odiaeresis', 'Adiaeresis', 'Udiaeresis', 'ssharp']


class AutocompleteCombobox(ttk.Combobox):
    """:class:`ttk.Combobox` widget that features autocompletion."""
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
        self['values'] = self._completion_list  # Setup our popup menu


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

            # No need for up/down, we'll jump to the popup
            # list at the position of the autocompletion

    def handle_return(self, event):
        """
        Function to bind to the Enter/Return key so if Enter is pressed the selection is cleared
        
        :param event: Tkinter event
        """
        self.icursor(tk.END)
        self.selection_clear()
        
        
#%% interface


# if __name__ == '__main__':
#         test_list = ('apple', 'banana', 'CranBerry', 'dogwood', 'alpha', 'Acorn', 'Anise' )
#         test(a)
        
###############################################
#               block 1                       #
###############################################
#                  #                          #
#                  #                          #
#                  #                          #
#   block 2        #     block 3              #
#                  #                          #
#                  #                          #
#                  #                          #
###############################################

        

        
                
class Root(tk.Tk):
        
    def __init__(self):
        self.IDXS = None
        self.shown_IDX = None
        self.save_path = None
        self.save_format = None
        super(Root, self).__init__()
        self.title("Tkinter First Window")

        # figure creation
        self.f = Figure(figsize=(4,3), dpi=100)

        gs = self.f.add_gridspec(1,50)
        self.a = self.f.add_subplot(gs[:,:-1])
        self.color = self.f.add_subplot(gs[:,-1])
        self.color.tick_params(labelsize=6)
        self.a.axis('off')
        self.color.axis('off')
        
        
# =============================================================================
#         Block 1
# =============================================================================
        self.indice_list = AutocompleteCombobox(self)
        self.indice_list["state"]= "disable" # initialement grise
        self.indice_list.set_completion_list([''])
        self.indice_list.grid(column=5, row=2, padx=10, pady=10)
        for binds in [self.indice_list]:
            self.indice_list.bind("<<ComboboxSelected>>", lambda event=None:
                         self.get_combobox_value())
            self.indice_list.bind("<Return>", lambda event=None:
                         self.get_combobox_value())
                
        self.sat_desc = tk.Label(self, text = "Fichier de données satellites :",
                            font = ("Arial Bold", 8), bg = 'black', fg = 'white')
        self.sat_desc.grid(column=0, row=0, padx=10, pady=10, rowspan =1, columnspan=3)

        self.sat_path = tk.Label(self, text = "Sélectionner un chemin", width=50,
                            font = ("Arial", 8), bg = 'white', fg = 'black')
        self.sat_path.grid(column=3, row=0, padx=10, pady=10, rowspan =1, columnspan=3)

        self.sat_bouton = tk.Button(self, name="sat", text = "Parcourir", bg = "orange" ,
                                fg = "blue", command = lambda : self.get_path("sat"))
        self.sat_bouton.grid(column=6, row=0, padx=10, pady=10, rowspan =1, columnspan=3)

        self.data_desc = tk.Label(self, text = "Image ONE-PIX :", font = ("Arial", 8),
                              bg = 'black', fg = 'white')
        self.data_desc.grid(column=0, row=1, padx=10, pady=(10,30), rowspan =1, columnspan=3)
        self.data_path = tk.Label(self, text = "Sélectionner un chemin", width=50,
                              font = ("Arial", 8), bg = 'white', fg = 'black')
        self.data_path.grid(column=3, row=1, padx=10, pady=(10,30), rowspan =1, columnspan=3)
        self.data_bouton = tk.Button(self, name="data", text = "Parcourir", bg = "orange" ,
                                fg = "blue", command = lambda : self.get_path("data"))
        self.data_bouton.grid(column=6, row=1, padx=10, pady=(10,30), rowspan =1, columnspan=3)

# =============================================================================
#         Block 2
# =============================================================================
        
        self.domain_desc = tk.Label(text = "domaine d'application :", bg = "black", fg = "white")
        self.domain_desc.grid(column=0, row=5, padx=10, pady=10, rowspan=1, columnspan=1)

        self.domain = ttk.Combobox(self)
        self.domain['values']= ("vegetation","snow","water")
        self.domain.current(0) #index de l'élément sélectionné
        self.domain.grid(column=1, row=5, padx=10, pady=10, rowspan=1, columnspan=1)    

        self.sort_choice = ttk.Combobox(self, textvariable = ("keep all", "simple filter"),
                                   state = "readonly")
        self.sort_choice['values']=["keep all", "siple filter"]
        self.sort_choice.current(0) #index de l'élément sélectionné
        self.sort_choice.grid(column=0, row=6, padx=10, pady=10, rowspan=1, columnspan=1)
        
        self.critere = ttk.Combobox(self, state = "disable")
        self.critere['values']= ("variance", "entropie")
        self.critere.current(0) #index de l'élément sélectionné
        self.critere.grid(column=0, row=7, padx=10, pady=10, rowspan=1, columnspan=1)
        
        self.nb_keep = tk.Entry(self ,font = ("Arial Bold", 10),
                           bg = 'white', fg = "black", state = "disable")
        self.nb_keep.grid(column=1, row=7, padx=10, pady=10, rowspan=1, columnspan=1)
        
        self.calc_bouton = tk.Button(self , text = "Afficher les indices",
                            bg = "red", fg = "blue",
                            command = lambda : self.calculation(),
                            state = "disabled")
        self.calc_bouton.grid(column=1, row=6, padx=10, pady=10, rowspan=1, columnspan=1)

        self.WIP = tk.Label(self, text = "Done", font = ("Arial Bold", 20),
                            bg = 'green', fg = "red")
        self.WIP.grid(column=0, row=8, padx=10, pady=10, rowspan=1, columnspan=1)

        self.Exit_bouton = tk.Button(self , text = "QUIT", bg = "red" , fg = "blue", command = self.destroy)
        self.Exit_bouton.grid(column=1, row=8, padx=10, pady=(10,10),rowspan=1, columnspan=1)

        self.sort_choice.bind("<<ComboboxSelected>>", lambda event=None:
                         self.get_mode_choice())
            
# =============================================================================
#         Block 3
# =============================================================================


        self.canvas = FigureCanvasTkAgg(self.f, self)
        self.canvas.get_tk_widget().grid(column=5, row=4, padx=10, pady=10, rowspan=5, columnspan=5)

        self.toolbarFrame = tk.Frame(master=self, width=100, height=100)
        self.toolbarFrame.grid(column=4, row=3, padx=10, pady=10, rowspan=1, columnspan=5)
        NavigationToolbar2Tk(self.canvas, self.toolbarFrame)

        self.scale = tk.Scale(self, orient='horizontal', from_=0, to_=0, length=300,
                          showvalue = 0, state = "disabled",
                          repeatdelay = 100,
                          command = self.plot_indices, var = self.shown_IDX)
        self.scale.grid(column=6, row=2, padx=10, pady=10, rowspan=1, columnspan=3)
        
        self.save_options = tk.Button(self, text = 'Save options', state = "disable",
                                      bg = "red", fg = "blue", command = self.save_menu)
        self.save_options.grid(column=6, row=9, padx=10, pady=10, rowspan=1, columnspan=1)
        
        self.save_confirm = tk.Button(self, text = 'Save', bg = "red", fg = "blue",
                                      state = "disable",
                                      command = self.save_data)
        
        self.save_confirm.grid(column=7, row=9, padx=10, pady=10, rowspan=1, columnspan=1)
        
        
# =============================================================================
#         popup sauvegarde
# =============================================================================

    def save_menu(self):
        self.d = tk.Toplevel(self)
        self.d.maxsize(500,400)
        self.d.attributes('-topmost', 'true')
        
        self.format_choice = ttk.Combobox(self.d, textvariable = ("PNG", "np array"),
                                    values = ["PNG", "np array"],
                                    state = "readonly")
        self.format_choice.current(0) #index de l'élément sélectionné
        self.format_choice.grid(column=0, row=0, padx=10, pady=10, rowspan =1, columnspan=2)
        
        self.save_desc = tk.Label(self.d, text = "dossier de sauvegarde :",
                        font = ("Arial Bold", 8), bg = 'black', fg = 'yellow')
        self.save_desc.grid(column=0, row=1, padx=10, pady=10, rowspan =1, columnspan=1)
    
        self.save_path_label = tk.Label(self.d, text = "Sélectionner un chemin",
                            font = ("Arial", 8), bg = 'white', fg = 'black')
        self.save_path_label.grid(column=0, row=2, padx=10, pady=10, rowspan =1, columnspan=2)
    
        self.explore_bouton = tk.Button(self.d, name="sat", text = "Parcourir", bg = "orange" ,
                                fg = "blue", command = lambda : self.get_dir())
        self.explore_bouton.grid(column=1, row=1, padx=10, pady=10, rowspan =1, columnspan=1)
        
        self.CANCEL_save_bouton = tk.Button(self.d, text = "Cancel",
                                            state = "normal", command = self.d.destroy)
        self.CANCEL_save_bouton.grid(column=2, row=3, padx=10, pady=10, rowspan =1, columnspan=1)
        
        self.confirm_bouton = tk.Button(self.d, text = "Confirm", state = "disable",
                                        command = self.check_path)
        self.confirm_bouton.grid(column=1, row=3, padx=10, pady=10, rowspan =1, columnspan=1)

# =============================================================================
#         pour le bind de la combobox des indices
# =============================================================================

    def get_combobox_value(self):
        idx = self.indice_list.get()
        self.shown_IDX = idx
        # self.scale.configure(showvalue=self.IDXS["names"].index(idx))
        self.scale.set(self.IDXS["names"].index(idx))
        self.update()
            
        
    
# =============================================================================
#         griser sur selection dans la combobox
# =============================================================================
    def get_mode_choice(self):
        sel = self.sort_choice.get()
        if sel == "keep all":
            self.critere.configure(state = "disable")
            self.nb_keep.configure(state = "disable")
            self.update()
        elif sel == "siple filter":
            self.critere.configure(state = "normal")
            self.nb_keep.configure(state = "normal")
            self.nb_keep.delete(0,tk.END)
            self.nb_keep.insert(0,"10")
        
        
        
# =============================================================================
#         demande des chemins pour le calcul
# =============================================================================
    def get_path(self, name = None):
        path = filedialog.askopenfilename()
        if name =="sat":
            if path.endswith(".csv"):
                self.sat_path.configure(text = path, bg = "white", fg = "black")
                
            else:
                self.sat_path.configure(text = path, bg = "red", fg = "blue")
                self.calc_bouton.configure(state = "disable", bg = "red", fg = "blue")
            
        else: #if name == "data"
            if path.endswith(".tif"):
                self.data_path.configure(text = path, bg = "white", fg = "black")
                
            else:
                self.data_path.configure(text = path, bg = "red", fg = "blue")
                self.calc_bouton.configure(state = "disable", bg = "red", fg = "blue")
    
        if (self.sat_path['text'].endswith(".csv") and self.data_path['text'].endswith(".tif")):
            self.calc_bouton.configure(state = "normal", bg = "white", fg = "black")
            
            
# =============================================================================
#             demande du dossier de sauvegarde
# =============================================================================
    def get_dir(self):
        path = filedialog.askdirectory()
        if path != "":
            self.confirm_bouton['state'] = "normal"
            self.save_path_label["text"] = path
            self.save_path = path
            self.save_format = self.format_choice.get()
                
        
        
    def plot_indices(self, val):
            VAL = int(val)
            self.a.axis('off')
            self.a.clear()
            self.a.set_title(self.IDXS["names"][VAL])
            self.color.clear()
            shw = self.a.imshow((self.IDXS["id"][VAL]))
            self.f.colorbar(shw, cax = self.color)
            self.f.canvas.draw_idle()
            self.scale.configure(label = self.IDXS["names"][VAL])
            self.indice_list.current(VAL)
    
    
    def calculation(self):
        self.scale["state"] = "disable"
        self.indice_list["state"] = "disable"
        self.save_options.configure(state = "disable", bg = "red", fg = "blue")
        self.WIP.configure(text = "Computing...", bg = 'red', fg = "green")
        self.update()
        id_names = [n for n in sp.indices if (sp.indices[n].application_domain==self.domain.get())]
        self.get_idx(id_names)
        for i in range(len(id_names)):
            indice = self.IDXS["id"][i]
            self.IDXS["id"][i] = indice/np.max(abs(indice))
        self.sort_idx()
        self.WIP.configure(text = "Done", bg = 'green', fg = "red")
        self.scale.configure(state = "normal", to_ = len(self.IDXS["names"]) - 1,
                              label = self.IDXS["names"][0])
        self.scale.set(0) #after the state = activate to provide refresh the label
        self.plot_indices(self.scale.get())
        self.indice_list["state"] = "normal"
        self.save_options.configure(state = "normal", bg = "white", fg = "black")
        self.indice_list.set_completion_list(self.IDXS["names"])
        self.indice_list.current(0)

    
        
    
            
            
# =============================================================================
#         fonction de réductiion du nombre d'indices affichés
# =============================================================================
    def sort_idx(self):
        if self.sort_choice.get() == "keep all": #delete constant images
            temp = {"id":[], "names":[]}
            for i in range(len(self.IDXS["names"])):
                if len(np.unique(self.IDXS["id"][i]))!=1:
                    temp["id"].append(self.IDXS["id"][i])
                    temp["names"].append(self.IDXS["names"][i])
            temp["id"] = np.asarray(temp["id"])
            self.IDXS = temp
            
        elif self.sort_choice.get() == "siple filter":
            nb = int(self.nb_keep.get())
            if nb>len(self.IDXS["names"]):
                nb = len(self.IDXS["names"])
            if self.critere.get() == "entropie":
                ENTR = [entropy(self.IDXS["id"][k]) for k in range(len(self.IDXS["names"]))]
                names = self.IDXS["names"]
                ids = self.IDXS["id"] #no need to set it as a list, sort will do
                ENTR, names, ids = zip(*sorted(zip(ENTR, names, ids), reverse=True))
                self.IDXS = {"id": np.asarray(ids[:nb]),
                        "names": names[:nb]}
                
            elif self.critere.get() == "variance":
                VAR = [np.var(self.IDXS["id"][k]) for k in range(len(self.IDXS["names"]))]
                names = self.IDXS["names"]
                ids = self.IDXS["id"] #no need to set it as a list, sort will do
                VAR, names, ids = zip(*sorted(zip(VAR, names, ids), reverse=True))
                self.IDXS = {"id": np.asarray(ids[:nb]),
                        "names": names[:nb]}
                
    
        
# =============================================================================
#         sauvegarde des indices calculés
# =============================================================================
    def save_data(self):
        self.save_confirm.configure(state = "disable", bg = "red", fg = "blue")
        self.WIP.configure(text = "Saving...", bg = 'red', fg = "green")
        if self.save_format == "PNG":
            for i in range(len(self.IDXS['names'])):
                temp_im = self.IDXS['id'][i]
                temp_im = temp_im + abs(temp_im.min())
                temp_im = 255 * (temp_im - temp_im.min())/(temp_im.max() - temp_im.min())
                cv2.imwrite(self.save_path+"/"+self.IDXS['names'][i] + ".png", 
                            np.uint8(temp_im))
        elif self.save_format == "np array":
            im = []
            for i in range(len(self.IDXS['names'])):
                im.append(self.IDXS['id'][i].reshape(-1))
            np.save(self.save_path+"/"+"indices", np.asarray(im))
            np.save(self.save_path+"/"+"indices_names", np.asarray(self.IDXS['names']))
        self.WIP.configure(text = "Done", bg = 'green', fg = "red")
                
    
        
    def check_path(self):
        self.save_path = self.save_path_label["text"]
        self.save_confirm.configure(state = "normal", bg = "white", fg = "black")
        self.d.destroy()
    
        
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
        df = pd.read_csv(self.sat_path["text"], delimiter=';', engine = 'c')
        df2=df.dropna(axis = 0, how = 'all').dropna(axis = 1, how = 'all')
        
        self.IM = {"IM" : tiff.imread(self.data_path["text"]),
                    "wl" : np.load([f for f in os.listdir(os.chdir(os.path.dirname(self.data_path["text"])))
                                    if f.startswith("wavelengths")][0])}
        bands = []
        f = []
        for i in range(1,len(df2.columns)):
            f.append(interpolate.interp1d(df2['WL'], df2[df2.columns[i]])(self.IM["wl"]))
            bands.append((self.IM["IM"]*(f[i-1].reshape(-1,1,1))).sum(axis = 0))
        bands = np.asarray(bands)
        
        self.IM["bands"] = bands #ajout des bandes dans le dictionnaire
        
        A,B,G,R,RE1,RE2,RE3,N,N2,any,WV,S1,S2 = list(bands[np.arange(13),:,:])
        bands = np.array([A,B,G,R,RE1,RE2,RE3,N,N2,WV,S1,S2])
        
        
        da = xr.DataArray(
            bands,
            dims = ("band","x","y"),
            coords = {"band":["Aerosols", "Blue", "Green", "Red",
                              "Red Edge 1", "Red Edge 2", "Red Edge 3",
                              "NIR", "NIR 2", "Water Vapour", "SWIR 1",
                              "SWIR 2"]}
            )
        
        idx = sp.computeIndex(
            index = idx_to_compute,
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
        
        
if __name__ == '__main__':
    root = Root()
    # root.geometry("800x900")
    root.mainloop()
