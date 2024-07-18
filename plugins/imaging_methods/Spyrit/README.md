

# Spyrit plugin #

## Introduction 

This plugin allows you to acquire measurements with ONE-PIX using the Walsh Hadamard pattern base for a spatial resolution of  32x32 pixel  then to reconstruct the hypercube using the [Spyrit repository](https://github.com/openspyrit/spyrit) to obtain a datacube with 64x64 spatial resolution. 

> [!WARNING]  
> Acquisitions can be done with a One Pix kit using a raspberry pi but reconstruction requires the use of torch currently uninstallable on raspberry pi. 
>It is recommended to use a ONE-PIX camera on a system compatible with Torch to run acquisition and the reconstruction of Hypercube with this plugin.


## Installation 


first go in the spyrit plugin direcory :install dependencies  
```
cd plugins\imaging_methods\Spyrit\install
```
install dependencies  :

```
pip install -r requirements.txt
```
> [!WARNING] 
>to use the cnn reconstruction of the hypercube it is necessary to download the spyrit models provided for this purpose. Due to file size issues, these models were not stored on the ONE-PIX repo. contact the POP team who will provide them to you

after getting the Spyrit templates change the path of the folder containing the templates in the spyrit_config json file in the conf folder


## Quick start 

to run acqusition and spyrit reconstruction just run the ONE-PIX [GUI](https://github.com/PhotonicsOpenProjects/ONE-PIX/wiki/5.-FIS-interface-user-manual)and select Spyrit 
 and select the spyrit imaging method from the drop-down menu (2) 


