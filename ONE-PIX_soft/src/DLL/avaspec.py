import sys
import ctypes
import struct
# from PyQt5.QtCore import *
from enum import Enum
import os
# import debugpy
if os.getcwd()[-12:]=='ONE-PIX_soft':
    path='./src/DLL/'
else:
    path = '../src/DLL/'
    
if 'linux' in sys.platform: # Linux will have 'linux' or 'linux2'
    # this is the DLL for ubuntu
    #lib = ctypes.CDLL("/home/mark/field_kit/DLL/libavs.so.0.9.9")

    # this is the DLL for raspbian
    lib = ctypes.CDLL(path + "libavs.so.0.2.0")
    func = ctypes.CFUNCTYPE
elif 'darwin' in sys.platform: # macOS will have 'darwin'
    lib = ctypes.CDLL(path + "libavs.0.dylib")
    func = ctypes.CFUNCTYPE
else: # Windows will have 'win32' or 'cygwin'
    import ctypes.wintypes
    if (ctypes.sizeof(ctypes.c_voidp) == 8): # 64 bit
        WM_MEAS_READY = 0x8001
        lib = ctypes.WinDLL(path + "avaspecx64.dll")
        func = ctypes.WINFUNCTYPE
    else:
        WM_MEAS_READY = 0x0401
        lib = ctypes.WinDLL(path + "avaspec.dll")
        func = ctypes.WINFUNCTYPE

AVS_SERIAL_LEN = 10
VERSION_LEN = 16
USER_ID_LEN = 64

class AvsIdentityType(ctypes.Structure):
  _pack_ = 1
  _fields_ = [("SerialNumber", ctypes.c_char * AVS_SERIAL_LEN),
              ("UserFriendlyName", ctypes.c_char * USER_ID_LEN),
              ("Status", ctypes.c_char)]

class MeasConfigType(ctypes.Structure):
  _pack_ = 1
  _fields_ = [("m_StartPixel", ctypes.c_uint16),
              ("m_StopPixel", ctypes.c_uint16),
              ("m_IntegrationTime", ctypes.c_float),
              ("m_IntegrationDelay", ctypes.c_uint32),
              ("m_NrAverages", ctypes.c_uint32),
              ("m_CorDynDark_m_Enable", ctypes.c_uint8), # nesting of types does NOT work!!
              ("m_CorDynDark_m_ForgetPercentage", ctypes.c_uint8),
              ("m_Smoothing_m_SmoothPix", ctypes.c_uint16),
              ("m_Smoothing_m_SmoothModel", ctypes.c_uint8),
              ("m_SaturationDetection", ctypes.c_uint8),
              ("m_Trigger_m_Mode", ctypes.c_uint8),
              ("m_Trigger_m_Source", ctypes.c_uint8),
              ("m_Trigger_m_SourceType", ctypes.c_uint8),
              ("m_Control_m_StrobeControl", ctypes.c_uint16),
              ("m_Control_m_LaserDelay", ctypes.c_uint32),
              ("m_Control_m_LaserWidth", ctypes.c_uint32),
              ("m_Control_m_LaserWaveLength", ctypes.c_float),
              ("m_Control_m_StoreToRam", ctypes.c_uint16)]

class DeviceConfigType(ctypes.Structure):
  _pack_ = 1
  _fields_ = [("m_Len", ctypes.c_uint16),
              ("m_ConfigVersion", ctypes.c_uint16),
              ("m_aUserFriendlyId", ctypes.c_char * USER_ID_LEN),
              ("m_Detector_m_SensorType", ctypes.c_uint8),                      
              ("m_Detector_m_NrPixels", ctypes.c_uint16),
              ("m_Detector_m_aFit", ctypes.c_float * 5),
              ("m_Detector_m_NLEnable", ctypes.c_bool),
              ("m_Detector_m_aNLCorrect", ctypes.c_double * 8),
              ("m_Detector_m_aLowNLCounts", ctypes.c_double),
              ("m_Detector_m_aHighNLCounts", ctypes.c_double),
              ("m_Detector_m_Gain", ctypes.c_float * 2),
              ("m_Detector_m_Reserved", ctypes.c_float),
              ("m_Detector_m_Offset", ctypes.c_float * 2),
              ("m_Detector_m_ExtOffset", ctypes.c_float),
              ("m_Detector_m_DefectivePixels", ctypes.c_uint16 * 30),
              ("m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothPix", ctypes.c_uint16),
              ("m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothModel", ctypes.c_uint8),
              ("m_Irradiance_m_IntensityCalib_m_CalInttime", ctypes.c_float),
              ("m_Irradiance_m_IntensityCalib_m_aCalibConvers", ctypes.c_float * 4096),
              ("m_Irradiance_m_CalibrationType", ctypes.c_uint8),
              ("m_Irradiance_m_FiberDiameter", ctypes.c_uint32),  
              ("m_Reflectance_m_Smoothing_m_SmoothPix", ctypes.c_uint16),
              ("m_Reflectance_m_Smoothing_m_SmoothModel", ctypes.c_uint8),
              ("m_Reflectance_m_CalInttime", ctypes.c_float),
              ("m_Reflectance_m_aCalibConvers", ctypes.c_float * 4096),
              ("m_SpectrumCorrect", ctypes.c_float * 4096),
              ("m_StandAlone_m_Enable", ctypes.c_bool),
              ("m_StandAlone_m_Meas_m_StartPixel", ctypes.c_uint16),
              ("m_StandAlone_m_Meas_m_StopPixel", ctypes.c_uint16),
              ("m_StandAlone_m_Meas_m_IntegrationTime", ctypes.c_float),
              ("m_StandAlone_m_Meas_m_IntegrationDelay", ctypes.c_uint32),
              ("m_StandAlone_m_Meas_m_NrAverages", ctypes.c_uint32),
              ("m_StandAlone_m_Meas_m_CorDynDark_m_Enable", ctypes.c_uint8), 
              ("m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage", ctypes.c_uint8),
              ("m_StandAlone_m_Meas_m_Smoothing_m_SmoothPix", ctypes.c_uint16),
              ("m_StandAlone_m_Meas_m_Smoothing_m_SmoothModel", ctypes.c_uint8),
              ("m_StandAlone_m_Meas_m_SaturationDetection", ctypes.c_uint8),
              ("m_StandAlone_m_Meas_m_Trigger_m_Mode", ctypes.c_uint8),
              ("m_StandAlone_m_Meas_m_Trigger_m_Source", ctypes.c_uint8),
              ("m_StandAlone_m_Meas_m_Trigger_m_SourceType", ctypes.c_uint8),
              ("m_StandAlone_m_Meas_m_Control_m_StrobeControl", ctypes.c_uint16),
              ("m_StandAlone_m_Meas_m_Control_m_LaserDelay", ctypes.c_uint32),
              ("m_StandAlone_m_Meas_m_Control_m_LaserWidth", ctypes.c_uint32),
              ("m_StandAlone_m_Meas_m_Control_m_LaserWaveLength", ctypes.c_float),
              ("m_StandAlone_m_Meas_m_Control_m_StoreToRam", ctypes.c_uint16),
              ("m_StandAlone_m_Nmsr", ctypes.c_int16),
              ("m_StandAlone_m_Reserved", ctypes.c_uint8 * 12), # SD Card, do not use
              ("m_Temperature_1_m_aFit", ctypes.c_float * 5),
              ("m_Temperature_2_m_aFit", ctypes.c_float * 5),
              ("m_Temperature_3_m_aFit", ctypes.c_float * 5),
              ("m_TecControl_m_Enable", ctypes.c_bool),
              ("m_TecControl_m_Setpoint", ctypes.c_float),
              ("m_TecControl_m_aFit", ctypes.c_float * 2),
              ("m_ProcessControl_m_AnalogLow", ctypes.c_float * 2),
              ("m_ProcessControl_m_AnalogHigh", ctypes.c_float * 2),
              ("m_ProcessControl_m_DigitalLow", ctypes.c_float * 10),
              ("m_ProcessControl_m_DigitalHigh", ctypes.c_float * 10),
              ("m_EthernetSettings_m_IpAddr", ctypes.c_uint32),
              ("m_EthernetSettings_m_NetMask", ctypes.c_uint32),
              ("m_EthernetSettings_m_Gateway", ctypes.c_uint32), 
              ("m_EthernetSettings_m_DhcpEnabled", ctypes.c_uint8), 
              ("m_EthernetSettings_m_TcpPort", ctypes.c_uint16),
              ("m_EthernetSettings_m_LinkStatus", ctypes.c_uint8),  
              ("m_Reserved", ctypes.c_uint8 * 9720),
              ("m_OemData", ctypes.c_uint8 * 4096)]

class DeviceStatus(Enum):
    UNKNOWN = 0
    USB_AVAILABLE = 1
    USB_IN_USE_BY_APPLICATION = 2
    USB_IN_USE_BY_OTHER = 3
    ETH_AVAILABLE = 4
    ETH_IN_USE_BY_APPLICATION = 5
    ETH_IN_USE_BY_OTHER = 6
    ETH_ALREADY_IN_USE_USB = 7              

def AVS_Init(a_Port = 0):
    """
    Initializes the communication interface with the spectrometers.
    
    :param a_Port: ID of port to be used, defined as follows; -1: Use both
    Ethernet(AS7010) and USB ports; 0: Use USB port; 256: Use Ethernet(AS7010)
    
    :return: Number of connected and/or found devices; ERR_CONNECTION_FAILURE,
    ERR_ETHCONN_REUSE
    """    
    prototype = func(ctypes.c_int, ctypes.c_int)
    paramflags = (1, "port",),
    AVS_Init = prototype(("AVS_Init", lib), paramflags)
    ret = AVS_Init(a_Port) 
    return ret 

def AVS_Done():
    """
    Closes the communication and releases internal storage.
    
    :return: SUCCESS
    """
    prototype = func(ctypes.c_int)
    AVS_Done = prototype(("AVS_Done",lib),)
    ret = AVS_Done()
    return ret    

def AVS_GetNrOfDevices():
    """
    Deprecated function, replaced by AVS_UpdateUSBDevices(). The functionality
    is identical.
    
    :return: Number of devices found.
    """
    prototype = func(ctypes.c_int)
    AVS_GetNrOfDevices = prototype(("AVS_GetNrOfDevices", lib),)
    ret = AVS_GetNrOfDevices()
    return ret

def AVS_UpdateUSBDevices():
    """
    Internally checks the list of connected USB devices and returns the number 
    of devices attached. If AVS_Init() was called with a_Port=-1, the return 
    value also includes the number of ETH devices.
    
    :return: Number of devices found.    
    """
    prototype = func(ctypes.c_int)
    AVS_UpdateUSBDevices = prototype(("AVS_UpdateUSBDevices", lib),)
    ret = AVS_UpdateUSBDevices()
    return ret

def AVS_UpdateETHDevices(listsize = 75):
    """
    Internally checks the list of connected ETH devices and returns the number 
    of devices attached. If AVS_Init() was called with a_Port=-1, the return 
    value also includes the number of USB devices.
    
    :param listsize: Required size for list of returned devices. Default value 
    is 75, the size of AvsIdentityType
    :return: Tuple containing the required list size (position 0) and 
    AvsIdentityType for each found device.
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(AvsIdentityType))
    paramflags = (1, "listsize",), (2, "requiredsize",), (2, "IDlist",),
    AVS_UpdateETHDevices = prototype(("AVS_UpdateETHDevices", lib), paramflags)
    ret = AVS_UpdateETHDevices(listsize)
    return ret    

def AVS_GetList(spectrometers = 1):
    """
    Returns device information for each spectrometer connected to the ports
    indicated at AVS_Init(). Wrapper function has been modified to 
    automatically update to correct listsize.
    
    :param spectrometers: number of spectrometers connected. function uses 
    default value of 1, and automatically corrects.
    :return: Tuple containing AvsIdentityType for each found device. Devices 
    are sorted by UserFriendlyName
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(AvsIdentityType*spectrometers))
    paramflags = (1, "listsize",), (2, "requiredsize",), (2, "IDlist",),
    PT_GetList = prototype(("AVS_GetList", lib), paramflags)
    reqBufferSize, spectrometerList = PT_GetList(spectrometers*75)
    if reqBufferSize != spectrometers*75:
        spectrometerList = AVS_GetList(reqBufferSize//75)
    return spectrometerList

def AVS_GetHandleFromSerial(deviceSerial):
    """
    Retrieves the AvsHandle for the spectrometer with serialnumber deviceSerial. 
    Recommend usng AVS_Activate.
    
    :param deviceSerial: The serialnumber of the spectrometer
    :type deviceSerial: str, bytes
    :return: AvsHandle, handle to be used in subsequent function calls
    """
    prototype = func(ctypes.c_int, ctypes.c_char_p)
    paramflags = (1, "deviceSerial",),
    AVS_Activate = prototype(("AVS_Activate", lib), paramflags)
    if type(deviceSerial) is str:
        deviceSerial = deviceSerial.encode("utf-8")
    ret = AVS_Activate(deviceSerial)
    return ret     


def AVS_Activate(deviceId):
    """
    Activates spectrometer for communication
    
    :param deviceId: The device identifier
    :type deviceId: AvsIdentityType
    :return: AvsHandle, handle to be used in subsequent function calls
    """
    prototype = func(ctypes.c_int, ctypes.POINTER(AvsIdentityType))
    paramflags = (1, "deviceId",),
    AVS_Activate = prototype(("AVS_Activate", lib), paramflags)
    ret = AVS_Activate(deviceId)
    return ret

def AVS_UseHighResAdc(handle, enable):
    """
    Sets the ADC range of the spectrometer readout.
    
    :param handle: AvsHandle of the spectrometer
    :param enable: Boolean, True enables 16 bit resolution (65535 max value), 
    false uses 14 bit resolution (16383 max value)
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_bool)
    paramflags = (1, "handle",), (1, "enable",),
    AVS_UseHighResAdc = prototype(("AVS_UseHighResAdc", lib), paramflags)
    ret = AVS_UseHighResAdc(handle, enable)
    return ret

def AVS_GetVersionInfo(handle, FPGAversion, FWversion, DLLversion):

    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_char * VERSION_LEN, ctypes.c_char * VERSION_LEN, ctypes.c_char * VERSION_LEN)
    paramflags = (1, "handle",), (2, "FPGAversion",), (2, "FWversion",), (2, "DLLversion",),
    AVS_GetVersionInfo =prototype(("AVS_GetVersionInfo", lib), paramflags) 
    ret = AVS_GetVersionInfo(handle)
    return ret

def AVS_PrepareMeasure(handle, measconf):
    """
    Prepares measurement on the spectrometer using the specificed configuration.
    :param handle: AvsHandle returned by AVS_Activate or others
    :param measconf: MeasConfigType containing measurement configuration.
    """    
    datatype = ctypes.c_byte * 41
    data = datatype()
    temp = datatype()
    temp = struct.pack("=HHfIIBBHBBBBBHIIfH", measconf.m_StartPixel,
                                              measconf.m_StopPixel,
                                              measconf.m_IntegrationTime,
                                              measconf.m_IntegrationDelay,
                                              measconf.m_NrAverages,
                                              measconf.m_CorDynDark_m_Enable,
                                              measconf.m_CorDynDark_m_ForgetPercentage,
                                              measconf.m_Smoothing_m_SmoothPix,
                                              measconf.m_Smoothing_m_SmoothModel,
                                              measconf.m_SaturationDetection,
                                              measconf.m_Trigger_m_Mode,
                                              measconf.m_Trigger_m_Source,
                                              measconf.m_Trigger_m_SourceType,
                                              measconf.m_Control_m_StrobeControl,
                                              measconf.m_Control_m_LaserDelay,
                                              measconf.m_Control_m_LaserWidth,
                                              measconf.m_Control_m_LaserWaveLength,
                                              measconf.m_Control_m_StoreToRam )

    # copy bytes from temp to data, otherwise you will get a typing error below
    # why is this necessary?? they have the same type to start with ??
    x = 0
    while (x < 41): # 0 through 40
        data[x] = temp[x]
        x += 1
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_byte * 41)
    paramflags = (1, "handle",), (1, "measconf",),  
    AVS_PrepareMeasure = prototype(("AVS_PrepareMeasure", lib), paramflags)
    ret = AVS_PrepareMeasure(handle, data)
    return ret

def AVS_Measure(handle, windowhandle, nummeas):
    """
    Starts measurement on the spectrometer.
    
    :param handle: AvsHandle of the spectrometer
    :param windowhandle: Window handle to notify application measurement result
    data is available. The library sends a Windows message to the window with 
    command WM_MEAS_READY, with SUCCESS, the number of scans that were saved in
    RAM (if enabled), or INVALID_MEAS_DATA as WPARM value and handle as LPARM 
    value. Use on Windows only, 0 to disable.
    :param nummeas: number of measurements to do. -1 is infinite, -2 is used to
    start Dynamic StoreToRam
    """
    if not (('linux' in sys.platform) or ('darwin' in sys.platform)):
        prototype = func(ctypes.c_int, ctypes.c_int, ctypes.wintypes.HWND, ctypes.c_uint16)
    else:
        prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint16)
    paramflags = (1, "handle",), (1, "windowhandle",), (1, "nummeas"),
    AVS_Measure = prototype(("AVS_Measure", lib), paramflags)
    ret = AVS_Measure(handle, windowhandle, nummeas) 
    return ret



def AVS_StopMeasure(handle):
    prototype = func(ctypes.c_int, ctypes.c_int)
    paramflags = (1, "handle",),
    AVS_StopMeasure = prototype(("AVS_StopMeasure", lib), paramflags)
    ret = AVS_StopMeasure(handle)
    return ret

def AVS_PollScan(handle):
    prototype = func(ctypes.c_bool, ctypes.c_int)
    paramflags = (1, "handle",),
    AVS_PollScan = prototype(("AVS_PollScan", lib), paramflags)
    ret = AVS_PollScan(handle)
    return ret
    
def AVS_GetScopeData(handle):
    """
    Returns the pixel values of the last performed measurement. Should be 
    called after the notification on AVS_Measure is triggered. 
    
    :param handle: the AvsHandle of the spectrometer
    :return timestamp: ticks count last pixel of spectrum is received by 
    microcontroller ticks in 10 microsecond units since spectrometer started
    :return spectrum: 4096 element array of doubles, pixels values of spectrometer
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_double * 4096))
    paramflags = (1, "handle",), (2, "timelabel",), (2, "spectrum",),
    AVS_GetScopeData = prototype(("AVS_GetScopeData", lib), paramflags)
    timestamp, spectrum = AVS_GetScopeData(handle)
    return timestamp, spectrum

def AVS_GetLambda(handle):
    """
    Returns the wavelength values corresponding to the pixels if available. 
    This information is stored in the Library during the AVS_Activate() procedure.
    
    :param handle: the AvsHandle of the spectrometer
    :return: 4096 element array of wavelength values for pixels. If the detector
    is less than 4096 pixels, zeros are returned for extra pixels.
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_double * 4096))
    paramflags = (1, "handle",), (2, "wavelength",),
    AVS_GetLambda = prototype(("AVS_GetLambda", lib), paramflags)
    ret = AVS_GetLambda(handle)
    return ret

def AVS_GetNumPixels(handle):
    """
    Returns the number of pixels of a spectrometer. This information is stored 
    in the Library during the AVS_Activate() procedure.
    
    :param handle: the AvsHandle of the spectrometer
    :return: unsigned integer, number of pixels in spectrometer
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_short))
    paramflags = (1, "handle",), (2, "numPixels",),
    AVS_GetNumPixels = prototype(("AVS_GetNumPixels",lib), paramflags)
    ret = AVS_GetNumPixels(handle)
    return ret    

def AVS_SetDigOut(handle, portId, value):
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.c_uint8)
    paramflags = (1, "handle",), (1, "portId",), (1, "value",),
    AVS_SetDigOut = prototype(("AVS_SetDigOut", lib), paramflags)
    ret = AVS_SetDigOut(handle, portId, value)
    return ret

def AVS_GetAnalogIn(handle, AnalogInId, AnalogIn):
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.POINTER(ctypes.c_float))
    paramflags = (1, "handle",), (1, "AnalogInId",), (2, "AnalogIn",),
    AVS_GetAnalogIn = prototype(("AVS_GetAnalogIn", lib), paramflags)
    ret = AVS_GetAnalogIn(handle, AnalogInId)
    return ret


def AVS_GetParameter(handle, size = 63484):
    """
    Returns the device information of the spectrometer.
    
    :param handle: the AvsHandle of the spectrometer
    :param size: size in bytes allocated to store DeviceConfigType
    :return: DeviceConfigType containing spectrometer configuration data
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(DeviceConfigType))
    paramflags = (1, "handle",), (1, "size",), (2, "reqsize",), (2, "deviceconfig",),
    AVS_GetParameter = prototype(("AVS_GetParameter", lib), paramflags)
    ret = AVS_GetParameter(handle, size)
    if ret[0] != size:
        ret = AVS_GetParameter(ret[0])
    return ret[1]

def AVS_SetParameter(handle, deviceconfig):
    datatype = ctypes.c_byte * 63484
    data = datatype()
    temp = datatype()
    temp = struct.pack("=HH64B" +
                       "BH5f?8ddd2ff2ff30H" +      # Detector
                       "HBf4096fBI" +              # Irradiance
                       "HBf4096f" +                # Reflectance
                       "4096f" +                   # SpectrumCorrect
                       "?HHfIIBBHBBBBBHIIfHH12B" + # StandAlone 
                       "5f5f5f" +                  # Temperature
                       "?f2f" +                    # TecControl
                       "2f2f10f10f " +             # ProcessControl
                       "IIIBHB" +                  # EthernetSettings
                       "9720B" +                   # Reserved
                       "4096B",                    # OemData
                       deviceconfig.m_Len,
                       deviceconfig.m_ConfigVersion,
                       deviceconfig.m_aUserFriendlyId,
                       deviceconfig.m_Detector_m_SensorType,
                       deviceconfig.m_Detector_m_NrPixels,
                       deviceconfig.m_Detector_m_aFit,
                       deviceconfig.m_Detector_m_NLEnable,
                       deviceconfig.m_Detector_m_aNLCorrect,
                       deviceconfig.m_Detector_m_aLowNLCounts,
                       deviceconfig.m_Detector_m_aHighNLCounts,
                       deviceconfig.m_Detector_m_Gain,
                       deviceconfig.m_Detector_m_Reserved,
                       deviceconfig.m_Detector_m_Offset,
                       deviceconfig.m_Detector_m_ExtOffset,
                       deviceconfig.m_Detector_m_DefectivePixels,
                       deviceconfig.m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothPix,
                       deviceconfig.m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothModel,
                       deviceconfig.m_Irradiance_m_IntensityCalib_m_CalInttime,
                       deviceconfig.m_Irradiance_m_IntensityCalib_m_aCalibConvers,
                       deviceconfig.m_Irradiance_m_CalibrationType,
                       deviceconfig.m_Irradiance_m_FiberDiameter,
                       deviceconfig.m_Reflectance_m_Smoothing_m_SmoothPix,
                       deviceconfig.m_Reflectance_m_Smoothing_m_SmoothModel,
                       deviceconfig.m_Reflectance_m_CalInttime,
                       deviceconfig.m_Reflectance_m_aCalibConvers,
                       deviceconfig.m_SpectrumCorrect,
                       deviceconfig.m_StandAlone_m_Enable,
                       deviceconfig.m_StandAlone_m_Meas_m_StartPixel,
                       deviceconfig.m_StandAlone_m_Meas_m_StopPixel,
                       deviceconfig.m_StandAlone_m_Meas_m_IntegrationTime,
                       deviceconfig.m_StandAlone_m_Meas_m_IntegrationDelay,
                       deviceconfig.m_StandAlone_m_Meas_m_NrAverages,
                       deviceconfig.m_StandAlone_m_Meas_m_CorDynDark_m_Enable, 
                       deviceconfig.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage,
                       deviceconfig.m_StandAlone_m_Meas_m_Smoothing_m_SmoothPix,
                       deviceconfig.m_StandAlone_m_Meas_m_Smoothing_m_SmoothModel,
                       deviceconfig.m_StandAlone_m_Meas_m_SaturationDetection,
                       deviceconfig.m_StandAlone_m_Meas_m_Trigger_m_Mode,
                       deviceconfig.m_StandAlone_m_Meas_m_Trigger_m_Source,
                       deviceconfig.m_StandAlone_m_Meas_m_Trigger_m_SourceType,
                       deviceconfig.m_StandAlone_m_Meas_m_Control_m_StrobeControl,
                       deviceconfig.m_StandAlone_m_Meas_m_Control_m_LaserDelay,
                       deviceconfig.m_StandAlone_m_Meas_m_Control_m_LaserWidth,
                       deviceconfig.m_StandAlone_m_Meas_m_Control_m_LaserWaveLength,
                       deviceconfig.m_StandAlone_m_Meas_m_Control_m_StoreToRam,
                       deviceconfig.m_StandAlone_m_Nmsr,
                       deviceconfig.m_StandAlone_m_Reserved,
                       deviceconfig.m_Temperature_1_m_aFit,
                       deviceconfig.m_Temperature_2_m_aFit,
                       deviceconfig.m_Temperature_3_m_aFit,
                       deviceconfig.m_TecControl_m_Enable,
                       deviceconfig.m_TecControl_m_Setpoint,
                       deviceconfig.m_TecControl_m_aFit,
                       deviceconfig.m_ProcessControl_m_AnalogLow,
                       deviceconfig.m_ProcessControl_m_AnalogHigh,
                       deviceconfig.m_ProcessControl_m_DigitalLow,
                       deviceconfig.m_ProcessControl_m_DigitalHigh,
                       deviceconfig.m_EthernetSettings_m_IpAddr,
                       deviceconfig.m_EthernetSettings_m_NetMask,
                       deviceconfig.m_EthernetSettings_m_Gateway,
                       deviceconfig.m_EthernetSettings_m_DhcpEnabled,
                       deviceconfig.m_EthernetSettings_m_TcpPort,
                       deviceconfig.m_EthernetSettings_m_LinkStatus,
                       deviceconfig.m_Reserved,
                       deviceconfig.m_OemData)
    x = 0
    while (x < 63484): # 0 through 63483
        data[x] = temp[x]
        x += 1
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_byte * 63484)
    paramflags = (1, "handle",), (1, "deviceconfig",),  
    AVS_SetParameter = prototype(("AVS_SetParameter", lib), paramflags)
    ret = AVS_SetParameter(handle, data)
    return ret

    
def AVS_SetSyncMode(handle, enable):
    """
    Disables/Enables support for synchronous measurement. Library takes care of 
    dividing Nmsr request into Nmsr number of single measurement requests.
    
    See AvaSpec Library Manual section 3.4.8 for more information on running 
    multiple spectrometers synchronized.
    
    :param handle: AvsHandle of the master device spectrometer.
    :param enable: Boolean, 0 disables sync mode, 1 enables sync mode 
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_bool)
    paramflags = (1, "handle",), (1, "enable",),
    AVS_SetSyncMode = prototype(("AVS_SetSyncMode", lib), paramflags)
    ret = AVS_SetSyncMode(handle, enable)
    return ret