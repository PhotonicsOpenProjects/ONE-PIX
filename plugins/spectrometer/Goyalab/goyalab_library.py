############################################################################################################
#                                       Indigo driver example code                                         #
#                                                                                                          #
#       Revision : 1.1                                                                                     #
#       Last revision date : 24/10/2022                                                                    #
#                                                                                                          #
############################################################################################################
#                                                                                                          #
#   Prerequisites:                                                                                         #
#       1. Identify the COM port corresponding to your device (COMx on Windows, /dev/ttySx on Linux)       #
#       2. Install Python (3.7 minimum ? Written on 3.8.5)
#       3. Install the required libraries with pip : pySerial, parse, time, numpy and matplotlib           #
#       4. Plug in and turn on your Indigo device, preferably up to date (written on firmware version 80)  #
#                                                                                                          #
#   How to use this example:                                                                               #
#       1. Change the DEVICE_PORT variable to a descriptor string that matches your configuration          #
#       2. Execute the script                                                                              #
#                                                                                                          #
#                                                                                                          #
############################################################################################################

import serial                       # pip install pySerial
from parse import parse             # necessary for parsing some commands
from dataclasses import dataclass   # necessary for parsing some commands
import time                         # used for timing in this example
import numpy as np                  # used for timing in this example
import matplotlib.pyplot as plt     # used for plotting in this example



############################################################################################################
################################################## DRIVER ##################################################
############################################################################################################

@dataclass
class IndigoBasicSettings:
    def __init__(self):
        firm_version             = 0 # ideally, 80 or later
        module_id                = 0 # Reserved
        isLambdaModeEnabled      = 0 # True if the device is configured to send data in the nanometer range
        isFullBitsModeEnabled    = 0 # True if the device is configured to send data using its highest dynamics setting
        isPolyCalibEnabled       = 0 # True if polynomial calibration is being used to compute the spectrum in the wavelength space. If not available, this is ignored.
        exposure_ms              = 0 # Current exposure setting of the device in milliseconds
        gain_raw                 = 0 # current RAW gain of the camera. For MT9M001-based devices (camId = 1), the unit is LINEAR (2-15). For IMX-based devices, the unit is dB (0-30)
        nbPixelsPerLine          = 0 # Number of pixels per raw data line
        nbRowsPerCapture         = 0 # number of lines in a bloc capture
        nbRowsPerImage           = 0 # Number of rows in a full sensor image
        camId                    = 0 # Camera id. 0 = invalid, 1 = MT9M001, 2 = IMX334, 3 = IMX464
        moduleSubversion         = 0 # Reserved
        nbSkippedRowsPerLine     = 0 # Number of skipped rows in between two captured lines in a bloc capture. Typically 0 for MT9M001 devices. 
        nbBitsCamera             = 0 # Bit depth of the image sensor, per pixel
        nbBitsData               = 0 # Bit depth of the captured spectrum, for internal calculations
        isDeviceFullRange        = 0 # True if the device uses enhaced capture mode (i.e. the bit depth of transferred data will be higher than the sensor pixel dynamics, due to internal binning)
        nbBitsDisplayed          = 0 # Maximum number of bits in the transferred data. Used for reconstructing the spectrum if the device is configured in fullRange AND in fullBit mode.
    firm_version            : int
    module_id               : int
    isLambdaModeEnabled     : int
    isFullBitsModeEnabled   : int
    isPolyCalibEnabled      : int
    exposure_ms             : int
    gain_raw                : int
    nbPixelsPerLine         : int
    nbRowsPerCapture        : int
    nbRowsPerImage          : int
    camId                   : int
    moduleSubversion        : int
    nbSkippedRowsPerLine    : int
    nbBitsCamera            : int
    nbBitsData              : int
    isDeviceFullRange       : int
    nbBitsDisplayed         : int

@dataclass
class IndigoRangeSettings:
    def __init__(self):
        self.start_wavelength    = 0 # in nanonmeters
        self.stop_wavelength     = 0 # in nanonmeters
        self.nb_points           = 0
        self.step                = 0 # in nanonmeters
    start_wavelength    : int
    stop_wavelength     : int
    nb_points           : int
    step                : float
    
def read_device_range(serial_handle):
    settings = IndigoRangeSettings()
    send_command("GADV", serial_handle) # Request the parameters from the device
    while(serial_handle.inWaiting() == 0):        # wait until the device answers
        time.sleep(0.0001)
    data_buffer = serial_handle.readline() # read the formatted string
    # Parse the data, depending on the packet version
    packet_version = 0
    data_buffer = data_buffer.decode()
    parsed = parse("GADV {} {}", data_buffer)
    try:
        packet_version = int(parsed[0])
    except:
        print("Error while parsing GADV version : cannot parse the version number")
    
    if packet_version == 0:
        print("Error while parsing GADV version : null version number")
    elif packet_version == 1:
        parsed = parse("GADV {} {} {} {} {} {}\r\n", data_buffer)
        settings.start_wavelength = int(parsed[3])
        settings.stop_wavelength = int(parsed[4])
        settings.nb_points = int(parsed[5])
    elif packet_version in [2,3]:
        parsed = parse("GADV {} {} {} {} {} {} {}\r\n", data_buffer)
        settings.start_wavelength = int(parsed[3])
        settings.stop_wavelength = int(parsed[4])
        settings.nb_points = int(parsed[5])
    else:
        print("Error while parsing GADV version : unknown packet version")

    settings.step = (settings.stop_wavelength-settings.start_wavelength)*1./settings.nb_points
    return settings

def read_device_info(serial_handle):
    settings = IndigoBasicSettings()
    send_command("GINF", serial_handle) # Request the parameters from the device
    while(serial_handle.inWaiting() == 0):        # wait until the device answers
        time.sleep(0.0001)
    data_buffer = serial_handle.readall() # read the byte array
    # parse the data
    if len(data_buffer) >= 18:
        settings.firm_version = int(data_buffer[0:2], 16)
        settings.module_id = int(data_buffer[2:4], 16)
        settings.isLambdaModeEnabled = int(data_buffer[4:6], 16)
        settings.isFullBitsModeEnabled = int(data_buffer[6:8], 16)
        settings.isPolyCalibEnabled = int(data_buffer[8:10], 16)
        settings.exposure_ms = int(data_buffer[10:14], 16)
        settings.gain_raw = int(data_buffer[14:18], 16)
    if len(data_buffer) >= 30:
        settings.nbPixelsPerLine = int(data_buffer[18:22], 16)
        settings.nbRowsPerCapture = int(data_buffer[22:26], 16)
        settings.nbRowsPerImage = int(data_buffer[26:30], 16)
    if len(data_buffer) >= 32:
        settings.camId = int(data_buffer[30:32], 16)
    if len(data_buffer) >= 34:
        settings.moduleSubversion = int(data_buffer[32:34], 16)
    if len(data_buffer) >= 36:
        settings.nbSkippedRowsPerLine = int(data_buffer[34:36], 16)
    if len(data_buffer) >= 42:
        settings.nbBitsCamera = int(data_buffer[36:38], 16)
        settings.nbBitsData = int(data_buffer[38:40], 16)
        settings.isDeviceFullRange = int(data_buffer[40:42], 16)
    if len(data_buffer) >= 44:
        settings.nbBitsDisplayed = int(data_buffer[42:44], 16)
    else:
        settings.nbBitsDisplayed = settings.nbBitsData
    return settings

def read_spectrum(range_settings, device_info, serial_handle):
    # Retrieve the expected length of the data packet, in points
    expectedLength = range_settings.nb_points
    if not device_info.isLambdaModeEnabled:
        expectedLength = device_info.nbPixelsPerLine
    # Retrieve the number of bytes per points
    bytes_per_point = 1
    if device_info.isFullBitsModeEnabled:
        if device_info.nbBitsDisplayed > 16:
            bytes_per_point = 4
        elif device_info.nbBitsDisplayed > 8:
            bytes_per_point = 2
        
    expectedLengthInBytes = expectedLength * bytes_per_point
    
    serial_handle.readline() # discard the start symbol "$$\r\n"
    data_buffer = serial_handle.read(expectedLengthInBytes) # read the spectral data
    serial_handle.read(2) # discard the "\r\n" terminating the spectral data
    serial_handle.readline() # discard the stop symbol "$$\r\n"

    if(len(data_buffer) < expectedLengthInBytes):
        print("Invalid array length when interpreting raw data into a spectrum")
        
    spectrum = []
    if(bytes_per_point == 1):
        spectrum = data_buffer
    elif (bytes_per_point == 2):
        spectrum = [data_buffer[2*i]*256 + data_buffer[2*i+1] for i in range(int(expectedLengthInBytes/2))]
    elif (bytes_per_point == 4):
        spectrum = [data_buffer[4*i] + data_buffer[4*i+1]*256 + data_buffer[4*i+2]*65535
                    + data_buffer[4*i+3]*16777216 for i in range(int(expectedLengthInBytes/4))]
    else:
        print("Invalid bytes_per_point when interpreting raw data into a spectrum")
    
    return spectrum

def start_capture(source_id, serial_handle):
    send_command("CPI0", serial_handle)

def config_gain_millidB(gain_mdB, serial_handle):
    gain_mdB = int(gain_mdB)
    char1 = (gain_mdB%256).to_bytes(1, 'big')
    char2 = int(gain_mdB/256).to_bytes(1, 'big')
    send_command(b'SGDB'+char1+char2, serial_handle)

def config_expousure_time_ms(expo_ms, serial_handle):
    expo_ms = int(expo_ms)
    char1 = (expo_ms%256).to_bytes(1, 'big')
    char2 = int(expo_ms/256).to_bytes(1, 'big')
    send_command(b'SINT'+char1+char2, serial_handle)
    
    
def config_fullbitmode(isEnabled, serial_handle):
    if isEnabled:
        send_command("FBM1", serial_handle)
    else:
        send_command("FBM0", serial_handle)
    
def config_lambdamode(isEnabled, serial_handle):
    if isEnabled:
        send_command("LBM1", serial_handle)
    else:
        send_command("LBM0", serial_handle)

def config_sensor_means(nb_rows,serial_handle):
    send_command(f"SNBR {nb_rows}",serial_handle)

def send_command(command_string, serial_handle):
    if(type(command_string)==str):
        command_string = command_string.encode()
    serial_handle.write(command_string+"\r\n".encode())

def config_livemode(isEnabled,serial_handle):
    if isEnabled:
        send_command("LIVE 1 0", serial_handle)
    else:
        send_command("LIVE 0", serial_handle)

# Connect, configure, capture
def indigo_connect(DEVICE_PORT, DEVICE_PORT_BAUDRATE):
    ser= serial.Serial(DEVICE_PORT, DEVICE_PORT_BAUDRATE, timeout=1)
     
    return ser
    

"""
#%%

############# USB PORT CONFIGURATION
DEVICE_PORT = '/dev/ttyACM0' # Port identification. Typically 'COMx' on Windows, '/dev/ttySx' on Linux
# Note : the DEVICE_PORT is likely to be different for each device and/or computer. On Windows, use the device manager to read this.

DEVICE_PORT_BAUDRATE = 115200 # All Indigo devcies communicate at 115200bps
#############

ser=indigo_connect(DEVICE_PORT, DEVICE_PORT_BAUDRATE)
indigo_set_integration_times(ser,tint_ms=350)
spectrumX=indigo_get_wl(ser)
spectrumY=indigo_get_spectrum(ser)


# Plot the spectrum
spectrumplot = plt.plot(spectrumX, spectrumY)
plt.show()
"""
