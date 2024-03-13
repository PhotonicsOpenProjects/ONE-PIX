# Ocean Insigth spectrometers installation 

## On the ONE-PIX raspberry pi 

Installing Seabreeze dependencies: 
```
sudo apt-get -y install libglu1
sudo apt-get -y install libaio1 libaio-dev
sudo apt-get -y install libglib2.0-0
sudo apt-get -y install libasound2
sudo apt-get -y install libusb-0.1-4
```

## configure rules.d
To configure Ocean Insight USB rules you need to copy the file the 10-oceanoptics.rules file stored in the [DLL folder](../ONE-PIX_soft/src/DLL) and paste it in the /etc/udev/rules.d folder of the Rapsberry pi.

For that copy/paste the 10-oceanoptics.rules in /etc/udev/rules.d folder with this command line:

```
sudo cp ~/Desktop/ONE-PIX/plugins/spectrometer/OceanInsight/10-oceanoptics.rules   /etc/udev/rules.d
```


