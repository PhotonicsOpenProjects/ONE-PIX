echo -e '\e[32mpython dependencies installation with pip'

echo -e '\033[0m_________________________________________________'
pip install -r rasp_requirements.txt

echo -e '\e[32m opencv python & dependencies installation with apt'
echo -e '\033[0m_________________________________________________'

sudo apt -y install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt -y install libxvidcore-dev libx264-dev
sudo apt -y install libfontconfig1-dev libcairo2-dev
sudo apt -y install libgdk-pixbuf2.0-dev libpango1.0-dev
sudo apt -y install libgtk2.0-dev libgtk-3-dev
sudo apt -y install libatlas-base-dev gfortran
sudo apt -y install libhdf5-dev libhdf5-serial-dev libhdf5-103
sudo apt -y install libqt5gui5 libqt5webkit5 libqt5test5 python3-pyqt5
sudo apt -y install python3-dev
sudo apt install python3-opencv
sudo apt-get install git-all build-essential libusb-dev
sudo apt-get install libopenblas-dev

echo -e '\e[32mcut and paste a new config.txt  in boot '
echo -e '\033[0m_________________________________________________'

sudo rm /boot/config.txt
sudo cp ~/Desktop/ONE-PIX/install/config.txt /boot

