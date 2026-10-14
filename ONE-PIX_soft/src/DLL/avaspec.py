import sys
import os
import inspect
import ctypes
import struct
#from PyQt5.QtCore import *

AVS_SERIAL_LEN = 10
VERSION_LEN = 16
DETECTOR_NAME_LEN = 20
USER_ID_LEN = 64
INVALID_AVS_HANDLE_VALUE = 1000
ERR_ETHCONN_REUSE = -27
SENS_HAMS9201 = 4
SENS_TCD1304 = 5
SENS_SU256LSB = 17
SENS_SU512LDB = 18
SENS_HAMS11639 = 22
SENS_HAMG9208_512 = 24
SENS_HAMS13496 = 26
SENS_HAMS11155_2048_02_DIFF = 30
SENSOR_OFFSET = 1
NUMBER_OF_SENSOR_TYPES = 31
NR_DEFECTIVE_PIXELS = 30
MAX_NR_PIXELS = 4096
CLIENT_ID_SIZE = 32

DSTR_STATUS_DSS_MASK = 0x01   # DSTR Sequence Stop (DSS) bit of MEASUREMENT_DSTR_STATUS->DMS
DSTR_STATUS_FOE_MASK = 0x02   # FIFO Overflow Error (FOE) bit of MEASUREMENT_DSTR_STATUS->DMS
DSTR_STATUS_IERR_MASK = 0x04  # Internal Error (IERR) bit of MEASUREMENT_DSTR_STATUS->DMS
root=os.getcwd().split('/')
if 'win' in sys.platform: root=os.getcwd().split('\\')
idx=root.index('ONE-PIX_soft')
path=''

for k in range(idx+1):
    if root[k]!='':
        path+=f"/{root[k]}"
path=os.path.abspath(path+'/src/DLL/')
if 'win' in sys.platform:path=path[3:]+'\\'
if 'linux' in sys.platform: # Linux will have 'linux' or 'linux2'
    # this is the DLL for ubuntu
    #lib = ctypes.CDLL("/home/mark/field_kit/DLL/libavs.so.0.9.9")

    # this is the DLL for raspbian
    lib = ctypes.CDLL(path + "/libavs.so")
    func = ctypes.CFUNCTYPE
elif 'darwin' in sys.platform: # macOS will have 'darwin'
    lib = ctypes.CDLL(path + "/libavs.0.dylib")
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
# if 'linux' in sys.platform: # Linux will have 'linux' or 'linux2'
#     lib = ctypes.CDLL("/usr/local/lib/libavs.so.0")
#     func = ctypes.CFUNCTYPE
# elif 'darwin' in sys.platform: # macOS will have 'darwin'
#     lib = ctypes.CDLL("/usr/local/lib/libavs.0.dylib")
#     func = ctypes.CFUNCTYPE
# else: # Windows will have 'win32' or 'cygwin'
#     import ctypes.wintypes
#     if (ctypes.sizeof(ctypes.c_voidp) == 8): # 64 bit
#         WM_MEAS_READY = 0x8001
#         lib = ctypes.WinDLL("./avaspecx64.dll")
#         func = ctypes.WINFUNCTYPE
#     else:
#         WM_MEAS_READY = 0x0401
#         lib = ctypes.WinDLL("./avaspec.dll")
#         func = ctypes.WINFUNCTYPE

class AvsIdentityType(ctypes.Structure):
  _pack_ = 1
  _fields_ = [("SerialNumber", ctypes.c_char * AVS_SERIAL_LEN),
              ("UserFriendlyName", ctypes.c_char * USER_ID_LEN),
              ("Status", ctypes.c_char)]

class BroadcastAnswerType(ctypes.Structure):
  _pack_ = 1
  _fields_ = [("InterfaceType", ctypes.c_uint8),
              ("serial", ctypes.c_char * AVS_SERIAL_LEN),
              ("port", ctypes.c_uint16),
              ("status", ctypes.c_uint8),
              ("RemoteHostIp", ctypes.c_uint32),
              ("LocalIp", ctypes.c_uint32),
              ("reserved", ctypes.c_uint8 * 4)]

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
              ("m_DynamicStorage", ctypes.c_uint8 * 12), # ex SD Card, do not use
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
              ("m_EthernetSettings_m_ClientIdType", ctypes.c_uint8),
              ("m_EthernetSettings_m_ClientIdCustom", ctypes.c_char * 32),
              ("m_EthernetSettings_m_Reserved", ctypes.c_uint8 * 79),
              ("m_Reserved", ctypes.c_uint8 * 9608),
              ("m_OemData", ctypes.c_uint8 * 4096)]

class DstrStatusType(ctypes.Structure):
  _pack_ = 1
  _fields_ = [("m_TotalScans", ctypes.c_uint32),
              ("m_UsedScans", ctypes.c_uint32),
              ("m_Flags", ctypes.c_uint32),
              ("m_IsStopEvent", ctypes.c_uint8),
              ("m_IsOverflowEvent", ctypes.c_uint8),
              ("m_IsInternalErrorEvent", ctypes.c_uint8),
              ("m_Reserved", ctypes.c_uint8)]

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
    
    :return: SUCCESS = 0
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

def AVS_UpdateETHDevices(spectrometers = 1):
    """
    Returns a list containing info on all responding Ethernet spectrometers

    :param spectrometers: number of spectrometers connected. function uses 
    default value of 1, and automatically corrects.
    :return: Tuple containing BroadcastAnswerType for each found device.
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(BroadcastAnswerType*spectrometers))
    paramflags = (1, "listsize",), (2, "requiredsize",), (2, "ETHlist",),
    PT_AVS_UpdateETHDevices = prototype(("AVS_UpdateETHDevices", lib), paramflags)
    reqBufferSize, ETHlist = PT_AVS_UpdateETHDevices(spectrometers*26)
    if reqBufferSize != spectrometers*26:
        ETHlist = AVS_UpdateETHDevices(reqBufferSize//26)
    return ETHlist   

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
    datatype = ctypes.c_byte * 75
    temp = datatype()
    x = 0
    while (x < 9): # 0 through 8
        temp[x] = deviceId.SerialNumber[x]
        x += 1
    temp[9] = 0
    x += 1    
    while (x<74): # 10 through 73
        temp[x] = 0
        x += 1
    temp[74] = int.from_bytes(deviceId.Status, byteorder='big')  #  cannot assign directly here
    prototype = func(ctypes.c_int, ctypes.c_byte * 75)
    paramflags = (1, "deviceId",),
    AVS_Activate = prototype(("AVS_Activate", lib), paramflags)
    ret = AVS_Activate(temp)
    return ret

def AVS_Deactivate(handle):
    """
    Deactivates spectrometer.
    
    :param handle: AvsHandle of the spectrometer
    :return: True when device successfully closed, False when handle not found
    """
    prototype = func(ctypes.c_bool, ctypes.c_int)
    prototype.restype = ctypes.c_bool
    paramflags = (1, "handle",),
    AVS_Deactivate = prototype(("AVS_Deactivate", lib), paramflags)
    ret = AVS_Deactivate(handle)
    return ret 

def AVS_UseHighResAdc(handle, enable):
    """
    Sets the ADC range of the spectrometer readout.
    
    :param handle: AvsHandle of the spectrometer
    :param enable: Boolean, True enables 16 bit resolution (65535 max value), 
    false uses 14 bit resolution (16383 max value)
    :return: SUCCESS = 0 or FAILURE <> 0
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_bool)
    paramflags = (1, "handle",), (1, "enable",),
    AVS_UseHighResAdc = prototype(("AVS_UseHighResAdc", lib), paramflags)
    ret = AVS_UseHighResAdc(handle, enable)
    return ret

def AVS_GetVersionInfo(handle):
    """
    Returns three version numbers of the used system. Note that the library does 
    not check the size of the buffers allocated by the caller!
    :param handle: AvsHandle returned by AVS_Activate or others
    :return: tuple of the three requested versionstrings (FPGA, FW and Library), 
    encoded in c_char
    """       
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_char * VERSION_LEN, ctypes.c_char * VERSION_LEN, ctypes.c_char * VERSION_LEN)
    paramflags = (1, "handle",), (2, "FPGAversion",), (2, "FWversion",), (2, "DLLversion",),
    AVS_GetVersionInfo = prototype(("AVS_GetVersionInfo", lib), paramflags) 
    ret = AVS_GetVersionInfo(handle)
    return ret    

def AVS_PrepareMeasure(handle, measconf):
    """
    Prepares measurement on the spectrometer using the specificed configuration.
    :param handle: AvsHandle returned by AVS_Activate or others
    :param measconf: MeasConfigType containing measurement configuration.
    :return: SUCCESS = 0 or FAILURE <> 0
    """    
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(MeasConfigType))
    paramflags = (1, "handle",), (1, "measconf",),  
    AVS_PrepareMeasure = prototype(("AVS_PrepareMeasure", lib), paramflags)
    ret = AVS_PrepareMeasure(handle, measconf)
    return ret

def AVS_Measure(handle, windowhandle, nummeas):
    """
    Starts measurement on the spectrometer, variant used for Windows messages or polling
    
    :param handle: AvsHandle of the spectrometer
    :param windowhandle: Window handle to notify application measurement result
    data is available. The library sends a Windows message to the window with 
    command WM_MEAS_READY, with SUCCESS, the number of scans that were saved in
    RAM (if enabled), or INVALID_MEAS_DATA as WPARM value and handle as LPARM 
    value. Use on Windows only, 0 to disable.
    :param nummeas: number of measurements to do. -1 is infinite, -2 is used to
    start Dynamic StoreToRam
    :return: SUCCESS = 0 or FAILURE <> 0
    """
    if not (('linux' in sys.platform) or ('darwin' in sys.platform)):
        prototype = func(ctypes.c_int, ctypes.c_int, ctypes.wintypes.HWND, ctypes.c_uint16)
    else:
        prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint16)
    paramflags = (1, "handle",), (1, "windowhandle",), (1, "nummeas"),
    AVS_Measure = prototype(("AVS_Measure", lib), paramflags)
    ret = AVS_Measure(handle, windowhandle, nummeas) 
    return ret

class AVS_MeasureCallbackFunc(object):
    def __init__(self, function):
        self.prototype = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        self.callback = self.prototype(function)    

def AVS_MeasureCallback(handle, cb, nummeas):
    """
    Starts measurement on the spectrometer, variant used with callbacks
    
    :param handle: AvsHandle of the spectrometer
    :param cb: address of the callback function that has to be defined in the user
    program, and will be called by the library
    :param nummeas: number of measurements to do. -1 is infinite, -2 is used to
    start Dynamic StoreToRam
    :return: SUCCESS = 0 or FAILURE <> 0
    """    
    prototype = func(ctypes.c_int, ctypes.c_int, cb.prototype, ctypes.c_uint16)
    paramflags = (1, "handle",), (1, "adres",), (1, "nummeas"),
    AVS_MeasureCallback = prototype(("AVS_MeasureCallback", lib), paramflags)
    ret = AVS_MeasureCallback(handle, cb.callback, nummeas)
    return ret

class AVS_DstrCallbackFunc(object):
    def __init__(self, function):
        self.prototype = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint))
        self.callback = self.prototype(function)

def AVS_SetDstrStatusCallback(handle, cb):
    """    
    Sets the address of the callback function the library will call periodically when
    using the DynamicStoreToRam feature
    
    :param handle: AvsHandle of the spectrometer
    :param cb: address of the callback function that has to be defined in the user
    program, and will be called by the library
    :return: SUCCESS = 0 or FAILURE <> 0
    """    
    prototype = func(ctypes.c_int, ctypes.c_int, cb.prototype)
    paramflags = (1, "handle",), (1, "adres",), 
    AVS_SetDstrStatusCallback = prototype(("AVS_SetDstrStatusCallback", lib), paramflags)
    ret = AVS_SetDstrStatusCallback(handle, cb.callback)
    return ret

def AVS_GetDstrStatus(handle):
    """    
    Get the status of the buffer used in the DynamicStoreToRam feature
    
    :param handle: AvsHandle of the spectrometer
    :return: DstrStatusType
    """      
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(DstrStatusType))
    paramflags = (1, "handle",), (2, "dstrstatus",),
    AVS_GetDstrStatus = prototype(("AVS_GetDstrStatus", lib), paramflags)
    ret = AVS_GetDstrStatus(handle)
    return ret

def AVS_StopMeasure(handle):
    """    
    Stops a running measurement
    
    :param handle: AvsHandle of the spectrometer
    :return: SUCCESS = 0 or FAILURE <> 0
    """      
    prototype = func(ctypes.c_int, ctypes.c_int)
    paramflags = (1, "handle",),
    AVS_StopMeasure = prototype(("AVS_StopMeasure", lib), paramflags)
    ret = AVS_StopMeasure(handle)
    return ret

def AVS_PollScan(handle):
    """    
    Will show whether new measurement data are available
    
    :param handle: AvsHandle of the spectrometer
    :return: 0 = no data available or 1 = data available
    """  
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

def AVS_GetSaturatedPixels(handle):
    """
    Returns the saturation values of the last performed measurement. Should be 
    called after AVS_GetScopeData. 
    
    :param handle: the AvsHandle of the spectrometer
    :return saturated: 4096 element array of bytes, 1 = saturated and 0 = not saturated
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint8 * 4096))    
    paramflags = (1, "handle",), (2, "saturated",),
    AVS_GetSaturatedPixels = prototype(("AVS_GetSaturatedPixels", lib), paramflags)
    saturated = AVS_GetSaturatedPixels(handle)
    return saturated 

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

def AVS_GetDigIn(handle, portId):
    """
    Returns the status of the specified digital input.
    
    :param handle: the AvsHandle of the spectrometer
    :param portId: the identifier of the digital input 
    :return: the value of the digital input, 0 = low and 1 = high
    """    
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8))
    paramflags = (1, "handle",), (1, "portId",), (2, "value",),
    AVS_GetDigIn = prototype(("AVS_GetDigIn", lib), paramflags)
    ret = AVS_GetDigIn(handle, portId) 
    return ret

def AVS_SetDigOut(handle, portId, value):
    """
    Sets the status of the specified digital output.
    
    :param handle: the AvsHandle of the spectrometer
    :param portId: the identifier of the digital output
    :param value: the value of the digital output, 0 = low and 1 = high 
    :return: SUCCESS = 0 or FAILURE <> 0 
    """       
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.c_uint8)
    paramflags = (1, "handle",), (1, "portId",), (1, "value",),
    AVS_SetDigOut = prototype(("AVS_SetDigOut", lib), paramflags)
    ret = AVS_SetDigOut(handle, portId, value)
    return ret

def AVS_SetPwmOut(handle, portId, frequency, dutycycle):
    """
    Selects the PWM functionality for the specified digital output.
    
    :param handle: the AvsHandle of the spectrometer
    :param portId: the identifier of the digital output
    :param frequency: the desired PWM frequency (500 - 300000 Hz)
    :param dutycycle: the percentage high time in one cycle (0-100)
    :return: SUCCESS = 0 or FAILURE <> 0 
    """       
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.c_uint32, ctypes.c_uint8)
    paramflags = (1, "handle",), (1, "portId",), (1, "frequency",), (1, "dutycycle",),
    AVS_SetPwmOut = prototype(("AVS_SetPwmOut", lib), paramflags)
    ret = AVS_SetPwmOut(handle, portId, frequency, dutycycle)
    return ret    

def AVS_GetAnalogIn(handle, portId):
    """
    Returns the status of the specified analog input.
    
    :param handle: the AvsHandle of the spectrometer
    :param portId: the identifier of the analog input 
    :return: the value of the analog input, in Volts (or degrees Celsius)
    """      
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.POINTER(ctypes.c_float))
    paramflags = (1, "handle",), (1, "portId",), (2, "value",),
    AVS_GetAnalogIn = prototype(("AVS_GetAnalogIn", lib), paramflags)
    ret = AVS_GetAnalogIn(handle, portId)
    return ret

def AVS_SetAnalogOut(handle, portId, value):
    """
    Sets the analog output value for the specified analog output.
    
    :param handle: the AvsHandle of the spectrometer
    :param portId: the identifier of the analog output
    :param value: the value of the analog output in Volts (0 - 5.0V) 
    :return: SUCCESS = 0 or FAILURE <> 0 
    """      
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.c_float)
    paramflags = (1, "handle",), (1, "portId",), (1, "value",),
    AVS_SetAnalogOut = prototype(("AVS_SetAnalogOut", lib), paramflags)
    ret = AVS_SetAnalogOut(handle, portId, value)
    return ret

def AVS_GetParameter(handle, size = 63484):
    """
    Returns the device information of the spectrometer.
    
    :param handle: the AvsHandle of the spectrometer
    :param size: size in bytes allocated to store DeviceConfigType
    :return: DeviceConfigType structure containing spectrometer configuration data
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(DeviceConfigType))
    paramflags = (1, "handle",), (1, "size",), (2, "reqsize",), (2, "deviceconfig",),
    AVS_GetParameter = prototype(("AVS_GetParameter", lib), paramflags)
    ret = AVS_GetParameter(handle, size)
    if ret[0] != size:
        ret = AVS_GetParameter(ret[0])
    return ret[1]

def AVS_SetParameter(handle, deviceconfig):
    """
    Overwrites the device information of the spectrometer with the specified values.
    The data is not checked. Use with care!
    
    :param handle: the AvsHandle of the spectrometer
    :param deviceconfig: the DeviceConfigType structure that will be sent to the spectrometer
    :return: SUCCESS = 0 or FAILURE <> 0 
    """   
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(DeviceConfigType))
    paramflags = (1, "handle",), (1, "deviceconfig",),  
    AVS_SetParameter = prototype(("AVS_SetParameter", lib), paramflags)
    ret = AVS_SetParameter(handle, deviceconfig)
    return ret

def AVS_ResetParameter(handle):
    """
    Resets the device information of the spectrometer to the factory defaults.
    This will result in the loss of all user changes made using AVS_SetParameter
    
    :param handle: the AvsHandle of the spectrometer
    :return: SUCCESS = 0 or FAILURE <> 0 
    """       
    prototype = func(ctypes.c_int, ctypes.c_int)
    paramflags = (1, "handle",),
    AVS_ResetParameter = prototype(("AVS_ResetParameter", lib), paramflags)
    ret = AVS_ResetParameter(handle)
    return ret 

def AVS_SetSyncMode(handle, enable):
    """
    Disables/Enables support for synchronous measurement. Library takes care of 
    dividing Nmsr request into Nmsr number of single measurement requests.
    
    See AvaSpec Library Manual section 3.4.8 for more information on running 
    multiple spectrometers synchronized.
    
    :param handle: AvsHandle of the master device spectrometer.
    :param enable: Boolean, 0 disables sync mode, 1 enables sync mode
    :return: SUCCESS = 0 or FAILURE <> 0 
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_bool)
    paramflags = (1, "handle",), (1, "enable",),
    AVS_SetSyncMode = prototype(("AVS_SetSyncMode", lib), paramflags)
    ret = AVS_SetSyncMode(handle, enable)
    return ret

def AVS_GetDeviceType(handle):
    """
    Returns the type of the spectrometer, defined by its PCB
    
    :param handle: the AvsHandle of the spectrometer
    :return: integer value, 0=unknown, 1=AS5216, 2=ASMINI, 3=AS7010
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_byte))
    paramflags = (1, "handle",), (2, "devicetype",),
    AVS_GetDeviceType = prototype(("AVS_GetDeviceType",lib), paramflags)
    ret = AVS_GetDeviceType(handle)
    return ret 

def AVS_GetDetectorName(handle, SensorType):
    """
    Returns the name of the detector inside the spectrometer.
    
    :param handle: the AvsHandle of the spectrometer
    :param Sensortype: byte value that defines the detector type, part of the Device Configuration
    :return: Detector name, encoded in c_char, a null terminated string
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_byte, ctypes.c_char * DETECTOR_NAME_LEN)
    paramflags = (1, "handle",), (1, "SensorType",), (2, "SensorName",), 
    AVS_GetDetectorName = prototype(("AVS_GetDetectorName", lib), paramflags) 
    ret = AVS_GetDetectorName(handle, SensorType)
    return ret 

def AVS_SetSensitivityMode(handle, enable):
    """
    Selects between LowNoise and HighSensitivity mode for certain detectors.
      
    :param handle: AvsHandle of the spectrometer.
    :param enable: unsigned integer, 0 sets LowNoise mode, 1 sets HighSensitivity mode 
    """
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_uint32)
    paramflags = (1, "handle",), (1, "enable",),
    AVS_SetSensitivityMode = prototype(("AVS_SetSensitivityMode", lib), paramflags)
    ret = AVS_SetSensitivityMode(handle, enable)
    return ret

def AVS_SetPrescanMode(handle, enable):
    """
    Selects between PreScan and ClearBuffer mode for the Toshiba 3648 detector.
      
    :param handle: AvsHandle of the spectrometer.
    :param enable: boolean, 0 sets ClearBuffer mode, 1 sets PreScan mode (default mode)
    """    
    prototype = func(ctypes.c_int, ctypes.c_int, ctypes.c_bool)
    paramflags = (1, "handle",), (1, "enable",),
    AVS_SetPrescanMode = prototype(("AVS_SetPrescanMode", lib), paramflags)
    ret = AVS_SetPrescanMode(handle, enable)
    return ret

def AVS_ResetDevice(handle):
    """
    Performs a hard reset on the given spectrometer.
      
    :param handle: AvsHandle of the spectrometer.
    :return: SUCCESS = 0 or FAILURE <> 0
    """     
    prototype = func(ctypes.c_int, ctypes.c_int)
    paramflags = (1, "handle",),
    AVS_ResetDevice = prototype(("AVS_ResetDevice", lib), paramflags)
    ret = AVS_ResetDevice(handle)
    return ret

def AVS_EnableLogging(enable):
    """
    Enables or disables writing debug information to a log file, called "avaspec.dll.log", located in your user directory.
    Implemented for Windows only.
    
    :param enable: Boolean, True enables logging, False disables logging
    :return: True = 1
    """    
    prototype = func(ctypes.c_int, ctypes.c_bool)
    paramflags = (1, "enable",),
    AVS_EnableLogging = prototype(("AVS_EnableLogging", lib), paramflags)
    ret = AVS_EnableLogging(enable)    
    return ret    
