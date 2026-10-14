#!/bin/bash

set -e

# Compatibilité Bookworm (PEP 668)
export PIP_BREAK_SYSTEM_PACKAGES=1

echo -e "\e[32mRaspberry Pi system dependencies installation"
echo -e "_________________________________________________\e[0m"

sudo apt update

sudo apt install -y \
    build-essential \
    git \
    gfortran \
    libusb-dev \
    libopenblas-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-tk \
    python3-opencv \
    python3-pyqt5 \
    python3-numpy \
    python3-scipy \
    python3-sklearn \
    python3-matplotlib \
    python3-pil \
    python3-pil.imagetk \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libfontconfig1-dev \
    libcairo2-dev \
    libgdk-pixbuf-2.0-dev \
    libpango1.0-dev \
    libgtk2.0-dev \
    libgtk-3-dev \
    libhdf5-dev \
    libqt5gui5t64 \
    libqt5test5t64

echo -e "\n\e[32mPython dependencies installation"
echo -e "_________________________________________________\e[0m"

python3 -m pip install --upgrade pip setuptools wheel

python3 -m pip install \
    analysis-pipeline \
    basic-treatments \
    imutils==0.5.4 \
    screeninfo==0.8.1 \
    spectral==0.22.4 \
    sympy \
    flask==3.1.3 \
    flask-socketio==5.6.1 \
    orjson \
    onepix-fis-common-function \
    onepix-fouriersplit \
    onepix-fouriershift \
    onepix-stub-camera \
    onepix-stub-spectrometer

echo -e "\n\e[32mOptional Raspberry Pi boot config"
echo -e "_________________________________________________\e[0m"

CONFIG_FILE="$(dirname "$0")/config.txt"

if [ -f "$CONFIG_FILE" ]; then
    sudo cp "$CONFIG_FILE" /boot/config.txt
    echo "config.txt copied to /boot/config.txt"
fi

echo -e "\n\e[32mRaspberry Pi setup completed successfully\e[0m"
