

# Spyrit plugin #

## Introduction 

This plugin allows you to acquire measurements with ONE-PIX using the Walsh Hadamard pattern base then to reconstruct the hypercube using the Spyrit repository. 

Acquisitions can be done with a One Pix kit using a raspberry pi but reconstruction requires the use of torch currently uninstallable on raspberry pi. 

It is recommended to use the reconstruction of Hypercube with this plugin on a system compatible with Torch.

## Installation 

first go in the spyrit plugin direcory :install dependencies  
```
cd plugins\imaging_methods\Spyrit
```
install dependencies  :

```
pip install -r requirements.txt
```

to use the cnn reconstruction of the hypercube it is necessary to download the spyrit models provided for this purpose. Due to file size issues, these models were not stored on the ONE-PIX repo. contact the POP team who will provide them to you