"""
Created on Tue Oct 12 16:07:13 2021

@author: grussias & mribes 
"""

import tkinter as tk
from tkinter import filedialog, messagebox,ttk
from tkinter.messagebox import askquestion,showwarning

from functools import partial
import PIL.Image, PIL.ImageTk


import matplotlib.pyplot as plt 
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import numpy as np
import sys
import os
import glob
import datetime
import json

sys.path.insert(0,os.path.abspath('../'))

from src.AcquisitionConfig import *
from src.DatacubeReconstructions import *
import src.datacube_analyse as hsa

version='1.0.0'
root_path=os.getcwd()
json_path="../acquisition_param_ONEPIX.json"
config = OPConfig(json_path)


app=tk.Tk()
app.title("ONEPIX GUI ("+version+")")
app_path=os.getcwd()
#app.iconbitmap(app_path +  "\\" + "Fourier.ico")
app.resizable(False, False)  # This code helps to disable windows from resizing

screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

window_height = 600
window_width = 1020

# x_cordinate = int((screen_width/2) - (window_width/2))
# y_cordinate = int((screen_height/2) - (window_height/2))

app.geometry("{}x{}+{}+{}".format(window_width, window_height, 0,0))

"""
GROUP WIDGET POSITION
"""

n = ttk.Notebook(app,height=window_height,width=window_width)   # widget creation
n.pack()
w1 = ttk.Frame(n)       # Add widget 1
w1.pack()
w2 = ttk.Frame(n)       # Add second widget
w2.pack()
n.add(w1, text='Acquisition')                    # Acquisition widget
n.add(w2, text='Reconstruction & Analysis')      # Reconstruction widget


#%% Functions widget 1

pos_figX=300
pos_figY=100    
        
pos_charX=20
pos_charY=0   

pos_coX=750
pos_coY=110

pos_pretestX=20
pos_pretestY=110

pos_paramX=20
pos_paramY=220

pos_acquirX=1000
pos_acquirY=400


def clear_graph_w1():
    
    fig = Figure(figsize=(4, 4), dpi=100)
    canvas = FigureCanvasTkAgg(fig, master=w1)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().place(x=pos_figX,y=pos_figY)

    toolbar = NavigationToolbar2Tk(canvas, w1)
    toolbar.update()
    toolbar.place(x=pos_figX,y=pos_figY-50)


def close_window(config):
    if messagebox.askokcancel("Quit", "Do you want to quit ?"):
        if config.spec_lib.DeviceName!='':
            config.spec_lib.spec_close()
        plt.close('all')
        app.quit()
        app.destroy()
        
def simple_acq_mode():
    simple_mode_button['state']="disabled"
    expert_mode_button['state']="normal"

    #button_wind_test["state"] = "disabled"
    button_acquire_spec["state"] = "disabled"
    # button_acquire_hyp["state"] = "normal"
    
    #entry_wind_heigth["state"] = "disabled"
    #entry_wind_width["state"] = "disabled"
    entry_integration_time['state']='disabled'
    entry_pattern_duration['state']='disabled'
    entry_begin_pause['state']='disabled'
    # entry_sn_spectro['state']='disabled'
    

def expert_acq_mode(): 
    expert_mode_button['state']="disabled"
    simple_mode_button['state']="normal"
    
    #button_wind_test["state"] = "normal"
    button_acquire_spec["state"] = "normal"
    # button_acquire_hyp["state"] = "normal"
    
    #entry_wind_heigth["state"] = "normal"
    #entry_wind_width["state"] = "normal"
    entry_integration_time['state']='normal'
    entry_pattern_duration['state']='normal'
    entry_begin_pause['state']='normal'
    # entry_sn_spectro['state']='normal'

def close_window_proj():
    global dim_proj
    
#     entry_wind_heigth.delete(0,'end')
#     entry_wind_width.delete(0,'end')
#     
#     entry_wind_heigth.insert(0, proj.winfo_height()-100)
#     entry_wind_width.insert(0, proj.winfo_width()-100)
# 
#     dim_proj=[proj.winfo_height()-100,proj.winfo_width()-100,proj.winfo_x(),proj.winfo_y()]
#     print(proj.winfo_x(),proj.winfo_y())
#     print(dim_proj)
    button_wind_test["state"] = "normal"
    plt.close('all')
    proj.quit()
    proj.destroy()

    
def _resize_image(event):
   

    img_pil = copy_of_pil_img.resize((proj.winfo_width()-100, proj.winfo_height()-100))
    
    img=PIL.ImageTk.PhotoImage(master=proj,image=img_pil)
    label.config(image = img)
    label.image=img


def window_size_test(config):
    global proj
    global copy_of_pil_img
    global label
    
    
    proj=tk.Tk()
    dim= str(config.width+100)+"x"+str(config.height+100)
    proj.geometry("{}x{}+{}+{}".format(config.width+25, config.height+25, 1000,0))

    proj.update()
            
    x=list(range(config.height)) # horizontal vector for the pattern creation 
    y=list(range(config.width))# vertical vector for the pattern creation
    Y,X = np.meshgrid(x,y)# horizontal and vertical array for the pattern creation
    A=2*np.pi*X*10/config.height
    B=2*np.pi*Y*10/config.width
    pos_r=np.cos(A+B) #gray pattern creation
    pos_r[pos_r<0]=0
    
    pil_img=PIL.Image.fromarray(255*pos_r)
    copy_of_pil_img=pil_img.copy()
    
    img=PIL.ImageTk.PhotoImage(master=proj,image = pil_img)
    label = tk.Label(proj, image=img)
    label.image=img 
    
    label.bind('<Configure>',_resize_image)
    label.pack()
    
    button_quit_proj=tk.Button(proj,text="Close",command=close_window_proj,bg="red")  
    button_quit_proj.pack()
    button_wind_test["state"] = "disabled"
    proj.update()
        


def connection(config):
    global label_led_co
    global button_acquire_hyp
    
    
    config.name_spectro=var2.get()
    config.spec_lib=SpectrometerBridge(config.name_spectro,config.integration_time_ms)
    config.spec_lib.spec_open()
    
    if config.spec_lib.DeviceName!='':
        label_led_co.destroy()
        label_led_co=tk.Label(w1,text="Connected",bg='green',width=10)
        label_led_co.place(x=pos_coX,y=pos_coY)
        entry_sn_spectro.delete(0,"end")
        entry_sn_spectro.insert(0,config.spec_lib.DeviceName)
        button_acquire_hyp["state"] = "normal"
        opt2["state"]="disabled"

    
def disconnection(config):  
    global label_led_co
    global button_acquire_hyp
    
    label_led_co.destroy()
    label_led_co=tk.Label(w1,text="Disconnected",bg='red')
    label_led_co.place(x=pos_coX,y=pos_coY)
    button_acquire_hyp["state"] = "disabled"

    if config.spec_lib.DeviceName!='' :
        config.spec_lib.spec_close()
        entry_sn_spectro.delete(0,"end")
        entry_sn_spectro.insert(0,"No device connected")
        opt2["state"]="normal"
    else :
        pass
    
    
def draw_spectrum(config):
    if (label_led_co['text']=='Connected'):
        config=entries_actualisation(config)
        clear_graph_w1()
        fig = Figure(figsize=(4, 4), dpi=100)
        a = fig.add_subplot(111)
        a.set_title("Acquired spectrum ")
        
        config.integration_time_ms=float(entry_integration_time.get())*1e3
        config.spec_lib.set_integration_time()
        
        a.plot(config.spec_lib.get_wavelengths(),config.spec_lib.get_intensities())
        a.set_xlabel("Wavelengths (nm)")
        a.set_ylabel("Intensity (counts)")
        canvas = FigureCanvasTkAgg(fig, master=w1)  # A tk.DrawingArea.
        canvas.draw()
        canvas.get_tk_widget().place(x=pos_figX,y=pos_figY)
        
        toolbar = NavigationToolbar2Tk(canvas, w1)
        toolbar.update()
        toolbar.place(x=pos_figX,y=pos_figY-50)
    
    else:
        showwarning("Warning", "Connect one spectrometer first")

def json_actualisation(config):
    global json_path
    global root_path
    os.chdir(root_path)
    file = open(json_path, "r")
    json_object = json.load(file)
    file.close()
    json_object["name_spectro"]=config.name_spectro
    json_object["pattern_method"]=var1.get() 
    json_object["spatial_res"]=int(entry_res_im.get())
    json_object["integration_time_ms"]=float(entry_integration_time.get())
    
    file = open(json_path, "w")
    json.dump(json_object,file)
    file.close()
    
def entries_actualisation(config):
    global entry_integration_time
    global entry_pattern_duration
    global entry_pattern_duration
    global entry_begin_pause
    global json_path
    
    json_actualisation(config)
    config.spec_lib.spec_close()
    config = OPConfig(json_path)
    config.spec_lib.spec_open()
    if (simple_mode_button['state']=="normal"):
            
        config.spec_lib.integration_time_ms= config.integration_time_ms
        config.spec_lib.set_integration_time()
        config.periode_pattern=int(entry_pattern_duration.get())
        config.begin_pause=int(entry_begin_pause.get()) 

    return config
    
def acquire_hyp(config):
    global proj
    # global entry_integration_time
    # global entry_pattern_duration
    plt.close('all')
    cv2.destroyAllWindows()
    # Entries actualisation
    config=entries_actualisation(config)
    
    if (simple_mode_button['state']=="disabled"):
        window_size_test(config)
        config=OP_init(config)
        close_window_proj()
        entry_integration_time['state']='normal'
        entry_integration_time.delete(0,"end")
        entry_integration_time.insert(0,config.integration_time_ms)
        entry_integration_time['state']='disabled'
        
        entry_pattern_duration['state']='normal'
        entry_pattern_duration.delete(0,"end")
        entry_pattern_duration.insert(0,config.periode_pattern)
        entry_pattern_duration['state']='disabled'
    
    if (button_wind_test["state"] == "disabled"):
        close_window_proj()
    
    # Start acquisition
    config=thread_acquisition(config)
    if (config.pattern_method in config.seq_basis or config.pattern_method=='Hadamard'):
        if len(config.spectra)>0:
            res=OPReconstruction(config.pattern_method,config.spectra,config.pattern_order)
            res.Selection()
            if config.pattern_method=='FourierShift':
                res.hyperspectral_image=res.hyperspectral_image[1:,1:,:] # Shift error correction
            # Reconstruct a RGB preview of the acquisition
            rgb_image=hsa.RGB_reconstruction(res.hyperspectral_image,config.wavelengths)
            # Display RGB image
            fig_color = Figure(figsize=(4, 4), dpi=100)
            a = fig_color.add_subplot(111)
            a.imshow(rgb_image)
            a.set_title("False RGB color of the hyperspectral image")
            canvas = FigureCanvasTkAgg(fig_color, master = w1)
            canvas.get_tk_widget().place(x=pos_figX,y=pos_figY)
              
            toolbar = NavigationToolbar2Tk(canvas, w1)
            toolbar.update()
            toolbar.place(x=pos_figX,y=pos_figY-50)
        elif config.pattern_method in config.full_basis:
            pass
    
    
    


#%% Widget 1 : Acquisition
"""
GROUP WIDGET POSITION
"""
    



"""
LABEL
"""    
# label_wind_heigth=tk.Label(w1,text="Height window: ") 
# label_wind_heigth.place(x=pos_pretestX,y=pos_pretestY+15)   
# 
# label_wind_width=tk.Label(w1,text="Width window: ")
# label_wind_width.place(x=pos_pretestX,y=pos_pretestY+55)

label_led_co=tk.Label(w1,text="Disconnected",bg='red')
label_led_co.place(x=pos_coX,y=pos_coY)

label_sn_spectro=tk.Label(w1,text="Serial number of the spectrometer: ")
label_sn_spectro.place(x=pos_coX,y=pos_coY+30)

label_integration_time=tk.Label(w1,text="Integration time (ms): ")
label_integration_time.place(x=pos_paramX,y=pos_paramY+35)

label_img_res=tk.Label(w1,text="Image resolution: ")
label_img_res.place(x=pos_paramX,y=pos_paramY+80)

label_pattern_pause=tk.Label(w1,text="Pattern duration (ms): ")
label_pattern_pause.place(x=pos_paramX,y=pos_paramY+125)

label_begin_pause=tk.Label(w1,text="Acquisition delay (s):")
label_begin_pause.place(x=pos_paramX,y=pos_paramY+170)



"""
ENTRIES
"""

entry_integration_time=tk.Entry(w1,width="5")
entry_integration_time.insert(0, config.integration_time_ms)
entry_integration_time.place(x=pos_paramX+160,y=pos_paramY+35)
entry_integration_time['state']='disabled'

entry_res_im=tk.Entry(w1,width="5")
entry_res_im.insert(0, 5)
entry_res_im.place(x=pos_paramX+160,y=pos_paramY+80)
entry_res_im['state']='normal'

entry_pattern_duration=tk.Entry(w1,width="5")
entry_pattern_duration.insert(0, config.periode_pattern)
entry_pattern_duration.place(x=pos_paramX+160,y=pos_paramY+125)
entry_pattern_duration['state']='disabled'

entry_begin_pause=tk.Entry(w1,width="5")
entry_begin_pause.insert(0,config.duree_dark)
entry_begin_pause.place(x=pos_paramX+160,y=pos_paramY+170)
entry_begin_pause['state']='disabled'

entry_sn_spectro=tk.Entry(w1)
entry_sn_spectro.insert(0,"No device connected")
entry_sn_spectro.place(x=pos_coX,y=pos_coY+60)
entry_sn_spectro['state']='normal'

# entry_sauv=tk.Entry(w1)
# entry_sauv.place(x=pos_coX,y=pos_acquirY+80)

"""
OPTION MENUES
"""
methods_list=['FourierSplit','FourierShift','Hadamard','Custom']
spectro_list=['Avantes','OceanInsight']

var1=tk.StringVar(w1)
var1.set(methods_list[0])
var2=tk.StringVar(w1)
var2.set(spectro_list[0])

opt1 = tk.OptionMenu(w1, var1, *methods_list)
opt1.config(width=10)
opt1.place(x=pos_coX,y=pos_acquirY-75)

opt2 = tk.OptionMenu(w1, var2, *spectro_list)
opt2.config(width=10)
opt2.place(x=pos_coX,y=pos_acquirY-110)

"""
BUTTONS
"""   

simple_mode_button = tk.Button(w1, text="Simple",command=simple_acq_mode,height=2,width=13,bg='tomato')
simple_mode_button.place(x=pos_pretestX-10,y=pos_pretestY-10)
simple_mode_button['state']="disabled"

expert_mode_button = tk.Button(w1, text="Expert",command=expert_acq_mode,height=2,width=13,bg='tomato')
expert_mode_button.place(x=pos_pretestX+120,y=pos_pretestY-10)
expert_mode_button['state']="normal"

button_wind_test=tk.Button(w1,text="Windows size test",command=partial(window_size_test,config),bg="cornflowerblue",height=1,width=20)  
button_wind_test.place(x=pos_paramX+20,y=pos_pretestY+75)
#button_wind_test["state"] = "disabled"

button_co=tk.Button(w1,text="Spectrometer connection",command=partial(connection,config),bg='chartreuse',height=1,width=24)
button_co.place(x=pos_coX,y=pos_coY+90)

button_acquire_hyp=tk.Button(w1,text="Acquire hypercube",command=partial(acquire_hyp,config),bg='gold',height=2,width=24)
button_acquire_hyp.place(x=pos_coX,y=pos_acquirY)
button_acquire_hyp["state"] = "disabled"

button_deco=tk.Button(w1,text="Spectrometer disconnection",command=partial(disconnection,config),bg='tomato',height=1,width=24)
button_deco.place(x=pos_coX,y=pos_coY+125)

button_acquire_spec=tk.Button(w1,text="Acquire spectrum",command=partial(draw_spectrum,config),bg='cornflowerblue',height=1,width=20)
button_acquire_spec.place(x=pos_paramX+20,y=pos_figY+360)
button_acquire_spec["state"] = "disabled"


"""
GRAPHS
"""

fig = Figure(figsize=(4, 4), dpi=100)
canvas = FigureCanvasTkAgg(fig, master=w1)  # A tk.DrawingArea.
canvas.draw()
canvas.get_tk_widget().place(x=pos_figX,y=pos_figY)

# toolbar = NavigationToolbar2Tk(canvas, w1)
# toolbar.update()
# toolbar.place(x=pos_figX,y=pos_figY-50)




#%% Functions widget 2 
global wavelengths
global data_cube
global rgb_cube

"""
Go to the main LOOP
"""
pos_figX2=300
pos_figY2=100   
        
pos_charX2=0
pos_charY2=0

pos_traitX=900
pos_traitY=150

pos_clustX=750
pos_clustY=300

pos_smoothX=900
pos_smoothY=410

pos_sauvX=50
pos_sauvY=650

def clear_graph():
    
    fig_img = Figure(figsize=(3, 3), dpi=100)
    canvas_img = FigureCanvasTkAgg(fig_img, master=w2)  # A tk.DrawingArea.
    canvas_img.draw()
    canvas_img.get_tk_widget().place(x=20,y=pos_figY2+100)

    toolbar_img = NavigationToolbar2Tk(canvas_img, w2)
    toolbar_img.update()
    toolbar_img.place(x=20,y=pos_figY2+50)

    fig_spec = Figure(figsize=(4, 4), dpi=100)
    canvas_spec = FigureCanvasTkAgg(fig_spec, master=w2)  # A tk.DrawingArea.
    canvas_spec.draw()
    canvas_spec.get_tk_widget().place(x=pos_figX+40,y=pos_figY2)

    toolbar_spec = NavigationToolbar2Tk(canvas_spec, w2)
    toolbar_spec.update()
    toolbar_spec.place(x=pos_figX2+40,y=pos_figY2-50)
    

def rgb_display(data_cube,wavelengths):
    
    rgb_cube=hsa.RGB_reconstruction(data_cube,wavelengths)
    
    fig_img = Figure(figsize=(3, 3), dpi=100)
    a = fig_img.add_subplot(111)
    a.imshow(rgb_cube)
    a.set_title("RGB reconstructed image")
    canvas_img = FigureCanvasTkAgg(fig_img, master=w2)  # A tk.DrawingArea.
    canvas_img.draw()
    canvas_img.get_tk_widget().place(x=20,y=pos_figY2+100)

    toolbar_img = NavigationToolbar2Tk(canvas_img, w2)
    toolbar_img.update()
    toolbar_img.place(x=20,y=pos_figY2+50)
    
    
        
def load_data():

    global wavelengths
    global data_cube
    global rgb_cube
    global header
    
    clear_graph()
    # Load raw data
    acq_data=load_spectra()
    wavelengths=acq_data['wavelengths']
    entry_borne_min.insert(0, round(wavelengths[0]))
    entry_borne_max.insert(0, round(wavelengths[-1]))

    # ONEPIX hypercube reconstruction
    res=OPReconstruction(acq_data['pattern_method'],acq_data["spectra"],acq_data['pattern_order'])
    res.Selection()
    if acq_data['pattern_method']=='FourierShift':
        res.hyperspectral_image=res.hyperspectral_image[1:,1:,:] # Shift error correction

    data_cube=res.hyperspectral_image
    rgb_display(data_cube,wavelengths)
    


def draw_spectra():
    mes=hsa.select_disp_spectra(data_cube,wavelengths,int(entry_nb_draw.get()),'single')
    
def rogn():
    global data_cube
    global wavelengths
    data_cube,wavelengths=hsa.clip_datacube(data_cube,wavelengths,round(float(entry_borne_min.get())),round(float(entry_borne_max.get())))
    rgb_display(data_cube,wavelengths)
    
def clustering():
    global data_cube
    global image_seg
    
    image_seg=hsa.clustering(data_cube,int(entry_acp.get()),int(entry_clust.get()))
    
    fig_spec = Figure(figsize=(4, 4), dpi=100)
    b = fig_spec.add_subplot(111)
    b.set_title("Clustered image ")
    b.imshow(image_seg)
    canvas_spec = FigureCanvasTkAgg(fig_spec, master = w2)
    canvas_spec.get_tk_widget().place(x=pos_figX2+40,y=pos_figY2)
    
    toolbar_spec = NavigationToolbar2Tk(canvas_spec, w2)
    toolbar_spec.update()
    toolbar_spec.place(x=pos_figX+40,y=pos_figY2-50)
    
def smoothing():
    global data_cube
    data_cube=hsa.smooth_datacube(data_cube,int(entry_smooth_box.get()),int(entry_smooth_order.get()))
    rgb_display(data_cube,wavelengths)

def refl_norm():
    global data_cube
    global wavelengths
    
    data_cube=hsa.Flux2Ref(data_cube,wavelengths)
    rgb_display(data_cube,wavelengths)
    
    
def save_data():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', 1)
    save_path = filedialog.askdirectory(title = "Select folder path to save data ")
    np.save(save_path+"\ONEPIX_analysed",data_cube)
    
#%% Widget 2 : Reconstruction & Analysis

"""
LABEL
"""    
label_borne_min=tk.Label(w2,text="Spectral bounds (nm):") 
label_borne_min.place(x=pos_clustX-5,y=pos_traitY+50)   

label_borne_max=tk.Label(w2,text="-")
label_borne_max.place(x=pos_clustX+50,y=pos_traitY+80) 

label_acp=tk.Label(w2,text="PCA dimensions:")
label_acp.place(x=pos_clustX-5,y=pos_clustY) 

label_clust=tk.Label(w2,text="Clusters: ")
label_clust.place(x=pos_clustX-5,y=pos_clustY+46) 

label_smooth_box=tk.Label(w2,text="Boxcar width:")
label_smooth_box.place(x=pos_clustX-5,y=pos_smoothY-6) 

label_smooth_order=tk.Label(w2,text="Polynomial order:")
label_smooth_order.place(x=pos_clustX-5,y=pos_smoothY+37)

label_sauv_doss=tk.Label(w2,text="Name folder for saving data:")
label_sauv_doss.place(x=pos_sauvX+150,y=pos_sauvY) 

"""
ENTRY
"""

entry_nb_draw=tk.Entry(w2,width="3")
entry_nb_draw.place(x=pos_clustX+135,y=pos_figY2+16)
entry_nb_draw.insert(0,5)

entry_acp=tk.Entry(w2,width="5")
entry_acp.place(x=pos_clustX,y=pos_clustY+23)

entry_clust=tk.Entry(w2,width="5")
entry_clust.place(x=pos_clustX,y=pos_clustY+69)


entry_borne_min=tk.Entry(w2,width="5")
entry_borne_min.place(x=pos_clustX,y=pos_traitY+80)

entry_borne_max=tk.Entry(w2,width="5")
entry_borne_max.place(x=pos_clustX+65,y=pos_traitY+80)


entry_smooth_box=tk.Entry(w2,width="5")
entry_smooth_box.place(x=pos_clustX,y=pos_smoothY+17) 

entry_smooth_order=tk.Entry(w2,width="5")
entry_smooth_order.place(x=pos_clustX,y=pos_smoothY+60) 

entry_sauv=tk.Entry(w2,width="5")
entry_sauv.place(x=pos_sauvX+150,y=pos_sauvY+20) 
    
    
"""
BOUTONS
"""   
button_clust=tk.Button(w2,text="Clustering",command=clustering,height=2,width=10,bg="cornflowerblue")
button_clust.place(x=pos_traitX-5,y=pos_clustY+20)

button_charg=tk.Button(w2,text="Load data",height=2,width=11,bg='gold',command=load_data)  
button_charg.place(x=20,y=pos_figY2-10)

button_norm=tk.Button(w2,text="Normalisation",height=2,width=11,bg='cornflowerblue',command=refl_norm)  
button_norm.place(x=145,y=pos_figY2-10)

button_show_sp=tk.Button(w2,text="Draw spectrum",command=draw_spectra)
button_show_sp.place(x=pos_clustX,y=pos_figY2+10)

button_rogn=tk.Button(w2,text="Trim spectra",command=rogn,height=2,width=10,bg="cornflowerblue")
button_rogn.place(x=pos_traitX-5,y=pos_traitY+58)

button_smooth=tk.Button(w2,text="Smoothing",command=smoothing,height=2,width=10,bg="cornflowerblue")
button_smooth.place(x=pos_traitX-5,y=pos_smoothY+10) 

button_sauv=tk.Button(w2,text="Save data",command=save_data,height=2,width=15,bg='gold')
button_sauv.place(x=pos_clustX+50,y=pos_smoothY+100) 


"""
GRAPHS
"""

fig_img = Figure(figsize=(3, 3), dpi=100)
canvas_img = FigureCanvasTkAgg(fig_img, master=w2)  # A tk.DrawingArea.
canvas_img.draw()
canvas_img.get_tk_widget().place(x=20,y=pos_figY2+100)

toolbar_img = NavigationToolbar2Tk(canvas_img, w2)
toolbar_img.update()
toolbar_img.place(x=20,y=pos_figY2+50)

fig_spec = Figure(figsize=(4, 4), dpi=100)
canvas_spec = FigureCanvasTkAgg(fig_spec, master=w2)  # A tk.DrawingArea.
canvas_spec.draw()
canvas_spec.get_tk_widget().place(x=pos_figX+40,y=pos_figY2)

toolbar_spec = NavigationToolbar2Tk(canvas_spec, w2)
toolbar_spec.update()
toolbar_spec.place(x=pos_figX2+40,y=pos_figY2-50)


"""
RADIO BUTTON 
"""
# var_charg = tk.IntVar(w2)
# var_charg.set(1)

# r1=tk.Radiobutton(w2,text="raw data",variable=var_charg,value =1).place(x=pos_charX,y=pos_charY)
# r2=tk.Radiobutton(w2,text="post trait data",variable=var_charg,value =2).place(x=pos_charX,y=pos_charY+20)


# var_sauv = tk.IntVar(w2)
# var_sauv.set(1)

# r1=tk.Radiobutton(w2,text="post trait data",variable=var_sauv,value =1).place(x=pos_sauvX,y=pos_sauvY) 
# r2=tk.Radiobutton(w2,text="gerbil format",variable=var_sauv,value =2).place(x=pos_sauvX,y=pos_sauvY+20) 

#%%
app.protocol("WM_DELETE_WINDOW",partial(close_window,config))
app.mainloop()
