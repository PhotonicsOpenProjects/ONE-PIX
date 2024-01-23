# Avantes spectrometers installation 


You need to update the /etc/udev/rules.d file of the raspberry pi to fix USB rules for Avantes Spectrometers.


To do so, go to this file with this command line: 
```
cd /etc/udev/rules.d
```
and add text in the file using these commands: 

```
sudo sed -i '13 i SUBSYSTEM=="usb", ATTRS{idVendor}=="1992", ATTRS{idProduct}=="0667", MODE="0666"' 99-com.rules
sudo sed -i '14 i SUBSYSTEM=="usb", ATTRS{idVendor}=="1992", ATTRS{idProduct}=="0668", MODE="0666"' 99-com.rules
sudo sed -i '15 i SUBSYSTEM=="usb", ATTRS{idVendor}=="1992", ATTRS{idProduct}=="0669", MODE="0666"' 99-com.rules
sudo sed -i '16 i SUBSYSTEM=="usb", ATTRS{idVendor}=="1992", ATTRS{idProduct}=="0670", MODE="0666"' 99-com.rules 

```
Finally, save and close the rules.d file.
