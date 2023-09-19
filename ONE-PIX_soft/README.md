# Readme for the ONE-PIX software installation #
# Introduction 

The installation of the ONE-PIX software is achievable as the hardware installation is fully completed..
To do so, you can follow the [hardware building tutorial](/hardware_build/hardware_building_tutorial.pdf) .
You can also buy an already premounted ONE-PIX  kit [here](https://www.photonics-bretagne.com/fr/product/imageur-hyperspectral-one-pix-pop/)

This tutorial details all the steps required to install the ONE-PIX software on a Raspberry Pi 4 board. 

# Installing the Raspberry Pi OS on the SD card and remote control

We recommend to use The ONE-PIX with a remote control Desktop.It allow you to run long acquisition in a more automated way. 

<p align="center">
<img src="imgs\remote_control.png" alt="remote control" width="500"/>
</p>
 

Here we assume that The ONE-PIX soft was developed to use a raspberry pi with Raspbian OS.
However it possible use directly your PC with python for more advanced performance. 

To install the Raspbian OS on the SD card you can follow steps on this link [here](https://www.raspberrypi.org/documentation/installation/installing-images/ )

To remote control your raspberry pi you can follow this tutorial [here](https://www.realvnc.com/en/blog/how-to-setup-vnc-connect-raspberry-pi/#:~:text=You%20can%20even%20create%20and,will%20be%20able%20to%20connect. )

# ONE-PIX software installation 

## Download git repository

The first step of this installation is to clone the ONE-PIX directory from Github.

From the Raspberry Pi, open a terminal and go to the desktop with the following command line:

```
cd Desktop
```

Download the ONE-PIX software from git 

```
sudo git clone https://github.com/PhotonicsOpenProjects/ONE-PIX.git
```

## Requirements installation

A folder ONE-PIX _soft was created on the desktop.
with the terminal go in this folder 

```
cd ONE-PIX/ONE-PIX_soft
```

You need to install Python packages to run ONE-PIX_soft. 
For that, just run the following command:

```
pip install -r requirements.txt
```

## Dependencies installation
More dependencies are requested to use OceanInsight spectrometers (Seabreeze) and the OpenCV library. 

Installing Seabreeze dependencies: 
```
sudo apt-get -y install libglu1
sudo apt-get -y install libaio1 libaio-dev
sudo apt-get -y install libglib2.0-0
sudo apt-get -y install libasound2
sudo apt-get -y install libusb-0.1-4
```

Installing OpenCV dependencies: 

```
sudo apt-get -y install build-essential cmake pkg-config
sudo apt -y install libjpeg-dev libtiff5-dev libjasper-dev libpng-dev
sudo apt -y install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt -y install libxvidcore-dev libx264-dev
sudo apt -y install libfontconfig1-dev libcairo2-dev
sudo apt -y install libgdk-pixbuf2.0-dev libpango1.0-dev
sudo apt -y install libgtk2.0-dev libgtk-3-dev
sudo apt -y install libatlas-base-dev gfortran
sudo apt -y install libhdf5-dev libhdf5-serial-dev libhdf5-103
sudo apt -y install libqt5gui5 libqt5webkit5 libqt5test5 python3-pyqt5
sudo apt -y install python3-dev
```

## Spectrometer rules configuration
You need to configure USB rules to allow data tranferts from your spectrometer.

If the spectrometer used is this [list of tested spectrometer](../ONE-PIX_soft/doc/tested_spectrometers.pdf) follow steps for your model. 

Else, the spectrometer used is not in this list, you need to see [adding a new spectrometer](https://one-pix.readthedocs.io/en/latest/contributing.html#adding-a-new-spectrometer) API section.

### Ocean Insight spectrometers 

To configure Ocean Insight USB rules you need to copy the file the 10-oceanoptics.rules file stored in the [DLL folder](../ONE-PIX_soft/src/DLL) and paste it in the /etc/udev/rules.d folder of the Rapsberry pi.

For that go to the DLL folder

```
cd src/DLL
```

and copy/paste the 10-oceanoptics.rules in /etc/udev/rules.d folder with this command line:

```
sudo cp 10-oceanoptics.rules   /etc/udev/rules.d
```

### Avantes spectrometers

You need to update the /etc/udev/rules.d file of the raspberry pi to fix USB rules for Avantes Spectrometers.


To do so, go to this file with this command line: 
```
cd /etc/udev/rules.d
```
and add text in the file ussing these commands: 

```
sudo sed -i '13 i SUBSYSTEM=="usb", ATTRS{idVendor}=="1992", ATTRS{idProduct}=="0667", MODE="0666"' 99-com.rules
sudo sed -i '14 i SUBSYSTEM=="usb", ATTRS{idVendor}=="1992", ATTRS{idProduct}=="0668", MODE="0666"' 99-com.rules
sudo sed -i '15 i SUBSYSTEM=="usb", ATTRS{idVendor}=="1992", ATTRS{idProduct}=="0669", MODE="0666"' 99-com.rules 

```
Finally, save and close the rules.d file.

## Activate Raspberry Pi camera 

to use ONE-PIX kit you need to activate the raspberry pi camera  for that go 


Enable SSH,VNC and the camera 

<p align="center">
<img src="imgs\interface_activation.JPG" alt="interface activation" width="300"/>
</p>




## Dual screen configuration
In order to perform ONE-PIX  measurements, it is necessary to set up a second screen dedicated to displaying the patterns to be projected on your scenes.
 
You need to change the boot/config.txt file of the Raspberry Pi to force the double screen stored in DLL folder. 
You need to supress your existing boot/config.txt and replace it by  preconfiguring config file stored in the[DLL folder](../ONE-PIX _soft/src/DLL).
For that use these command lines : 
```
sudo rm /boot/config.txt
sudo cp Desktop/ONE-PIX/ONE-PIX_soft/config.txt /boot
```
# Finalisation and checking of the installation

First, shutdown the Raspberry Pi and replug in the hardware benchtop. 
Then, plug the mini HDMI on the HDMI1 port.  
Power on the projector and the Raspebrry Pi board. 
Remote control your Pi with your computer.

Now, you need to configure screen display. For that, go in the screen configuration menu:

<p align="center">
<img src="imgs\screen_configuration_path.png" alt="screen configuration menu path " width="500"/>
</p>

This window will pop up:

<p align="center">
<img src="imgs\screen_menu.png" alt="screen configuration menu " width="200"/>
</p>

The HDMI1 and HDMI2 are superimposed. You need to grab HMDI 2 at the right of HDMI 1 with the mouse. 

<p align="center">
<img src="imgs\double screen.PNG" alt="double screen" width="200"/>
</p>

Now with VNC Viewer you can see two screens. The first one is the screen of the Raspberry
Pi desktop and the second is the screen of the projector. 

set the resolution of the screen 1 with 1024x768 pix and the screen 2 in 600x800pix. 

click one the green ticks to validate changes.

:warning: **Warning:** For long acquisition it may be necessary to deactivate the sleepmode. you can follow this [tutorial](https://pimylifeup.com/raspberry-pi-screensaver/)

<p align="center">
<img src="imgs\double_screen.png" alt="vnc vnc viewer double screen" width="500"/>
</p>

The installation is now complete. 
Now you can follow the [tutorial measure hyperspectral image](/ONE-PIX_soft/doc/tutorial_measure_hyperspectral_image.pdf) to measure your first hyperspectral datacube ! 













