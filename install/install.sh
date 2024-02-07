echo 'python dependencies installation with pip'

pip install -r requirements.txt

echo 'opencv python dependencies insatllation with apt'

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

echo 'cut and paste a new config.txt  in boot '

sudo rm /boot/config.txt
sudo cp ~/Desktop/ONE-PIX/install/config.txt /boot
