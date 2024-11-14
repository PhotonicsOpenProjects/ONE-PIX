#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging
import sys
import time
import math
import smbus


AS7341_ADDRESS     =  (0X39)

AS7341_ASTATUS    = (0X60)

AS7341_CONFIG    =  (0X70)
AS7341_STAT      =  (0X71)
AS7341_EDGE      =  (0X72)
AS7341_CPIO      =  (0X73)
AS7341_LED       =  (0X74)

AS7341_ENABLE    =  (0X80)
AS7341_ATIME     =  (0X81)
AS7341_WTIME     =  (0X83)

AS7341_SP_TH_L_LSB =(0X84)
AS7341_SP_TH_L_MSB =(0X85)
AS7341_SP_TH_H_LSB =(0X86)
AS7341_SP_TH_H_MSB =(0X87)
AS7341_AUXID       =(0X90)
AS7341_REVID      = (0X91)

AS7341_ID         = (0X92)
AS7341_STATUS_1   = (0X93)



AS7341_CH0_DATA_L = (0X95)
AS7341_CH0_DATA_H = (0X96)
AS7341_CH1_DATA_L = (0X97)
AS7341_CH1_DATA_H = (0X98)
AS7341_CH2_DATA_L = (0X99)
AS7341_CH2_DATA_H = (0X9A)
AS7341_CH3_DATA_L = (0X9B)
AS7341_CH3_DATA_H = (0X9C)
AS7341_CH4_DATA_L = (0X9D)
AS7341_CH4_DATA_H = (0X9E)
AS7341_CH5_DATA_L = (0X9F)
AS7341_CH5_DATA_H = (0XA0)

AS7341_STATUS_2  =  (0XA3)
AS7341_STATUS_3  =  (0XA4)
AS7341_STATUS_5  =  (0XA6)
AS7341_STATUS_6  =  (0XA7)
AS7341_CFG_0     =  (0XA9)
AS7341_CFG_1     =  (0XAA)
AS7341_CFG_3     =  (0XAC)
AS7341_CFG_6     =  (0XAF)
AS7341_CFG_8     =  (0XB1)
AS7341_CFG_9     =  (0XB2)
AS7341_CFG_10    =  (0XB3)
AS7341_CFG_12    =  (0XB5)


AS7341_PERS        =  (0XBD)
AS7341_GPIO_2      =  (0XBE)
AS7341_ASTEP_L     =  (0XCA)
AS7341_ASTEP_H     =  (0XCB)
AS7341_AGC_GAIN_MAX = (0XCF)
AS7341_AZ_CONFIG    = (0XD6)
AS7341_FD_TIME_1    = (0XD8)
AS7341_TIME_2       = (0XDA)
AS7341_CFG0         = (0XD7)
AS7341_STATUS       = (0XDB)
AS7341_INTENAB      = (0XF9)
AS7341_CONTROL      = (0XFA)
AS7341_FIFO_MAP     = (0XFC)
AS7341_FIFO_LVL     = (0XFD)
AS7341_FDATA_L      = (0XFE)
AS7341_FDATA_H      = (0XFF)

true                =      1
false               =      0
INPUT               =      0
OUTPUT              =      1
eF1F4ClearNIR       =      0
eF5F8ClearNIR       =      1
eSpm                =      0
eSyns               =      1
eSynd               =      3

class AS7341:
    def __init__(self, address=AS7341_ADDRESS):
        self.i2c = smbus.SMBus(1)
        self.address = address
        
        self.channel1 = 0
        self.channel2 = 0
        self.channel3 = 0
        self.channel4 = 0
        self.channel5 = 0
        self.channel6 = 0
        self.channel7 = 0
        self.channel8 = 0
        self.CLEAR = 0
        self.NIR = 0
               
        self.AS7341_Enable(true)
        measureMode = eSpm
        #--------------------------
        
    def Read_Byte(self, Addr):
        return self.i2c.read_byte_data(self.address, Addr)
        
    def Read_Word(self, Addr):
        return self.i2c.read_word_data(self.address, Addr)

    def Write_Byte(self, Addr, val):
        self.i2c.write_byte_data(self.address, Addr, val )
        
    def AS7341_Enable(self,flag):
        data = self.Read_Byte(AS7341_ENABLE)
        if flag == true:
            data = data | (1<<0)
        else:
            data = data & (~1)
        self.Write_Byte(AS7341_ENABLE,data)
        self.Write_Byte(0x00,0x30)

    def AS7341_EnableSpectralMeasure(self,flag):
        data=self.Read_Byte(AS7341_ENABLE)
        if(flag == true):
            data = data | (1<<1)
        else:
            data = data & (~(1<<1))
        self.Write_Byte(AS7341_ENABLE,data) 
   
    def AS7341_EnableSMUX(self,flag):   
        data=self.Read_Byte(AS7341_ENABLE)
        if(flag == true):
            data = data | (1<<4)
        else: 
            data = data & (~(1<<4))
        self.Write_Byte(AS7341_ENABLE,data) 
        
    def AS7341_EnableFlickerDetection(self,flag):
        data=self.Read_Byte(AS7341_ENABLE)
        if(flag == true):
            data = data | (1<<6)
        else:
            data = data & (~(1<<6))
        self.Write_Byte(AS7341_ENABLE,data)
        
    def AS7341_Config(self,mode):
        self.AS7341_SetBank(1)
        data=self.Read_Byte(AS7341_CONFIG)
        if mode == eSpm :
            data = (data & (~3)) | eSpm 
        elif mode == eSyns:        
            data = (data & (~3)) | eSyns
        elif mode == eSynd:
            data = (data & (~3)) | eSynd
        self.Write_Byte(AS7341_CONFIG,data)
        self.AS7341_SetBank(0)
        
    def F1F4_Clear_NIR(self):
        self.Write_Byte(0x00, 0x30) 
        self.Write_Byte(0x01, 0x01) 
        self.Write_Byte(0x02, 0x00) 
        self.Write_Byte(0x03, 0x00) 
        self.Write_Byte(0x04, 0x00) 
        self.Write_Byte(0x05, 0x42) 
        self.Write_Byte(0x06, 0x00) 
        self.Write_Byte(0x07, 0x00) 
        self.Write_Byte(0x08, 0x50) 
        self.Write_Byte(0x09, 0x00) 
        self.Write_Byte(0x0A, 0x00) 
        self.Write_Byte(0x0B, 0x00) 
        self.Write_Byte(0x0C, 0x20) 
        self.Write_Byte(0x0D, 0x04) 
        self.Write_Byte(0x0E, 0x00) 
        self.Write_Byte(0x0F, 0x30) 
        self.Write_Byte(0x10, 0x01) 
        self.Write_Byte(0x11, 0x50) 
        self.Write_Byte(0x12, 0x00) 
        self.Write_Byte(0x13, 0x06)    
        
    def F5F8_Clear_NIR(self):
        self.Write_Byte(0x00, 0x00) 
        self.Write_Byte(0x01, 0x00) 
        self.Write_Byte(0x02, 0x00) 
        self.Write_Byte(0x03, 0x40) 
        self.Write_Byte(0x04, 0x02) 
        self.Write_Byte(0x05, 0x00) 
        self.Write_Byte(0x06, 0x10) 
        self.Write_Byte(0x07, 0x03) 
        self.Write_Byte(0x08, 0x50) 
        self.Write_Byte(0x09, 0x10) 
        self.Write_Byte(0x0A, 0x03) 
        self.Write_Byte(0x0B, 0x00) 
        self.Write_Byte(0x0C, 0x00) 
        self.Write_Byte(0x0D, 0x00) 
        self.Write_Byte(0x0E, 0x24) 
        self.Write_Byte(0x0F, 0x00) 
        self.Write_Byte(0x10, 0x00) 
        self.Write_Byte(0x11, 0x50) 
        self.Write_Byte(0x12, 0x00) 
        self.Write_Byte(0x13, 0x06)   
    
    def FDConfig(self):    
        self.Write_Byte(0x00, 0x00) 
        self.Write_Byte(0x01, 0x00) 
        self.Write_Byte(0x02, 0x00) 
        self.Write_Byte(0x03, 0x00) 
        self.Write_Byte(0x04, 0x00) 
        self.Write_Byte(0x05, 0x00) 
        self.Write_Byte(0x06, 0x00) 
        self.Write_Byte(0x07, 0x00) 
        self.Write_Byte(0x08, 0x00) 
        self.Write_Byte(0x09, 0x00) 
        self.Write_Byte(0x0A, 0x00) 
        self.Write_Byte(0x0B, 0x00) 
        self.Write_Byte(0x0C, 0x00) 
        self.Write_Byte(0x0D, 0x00) 
        self.Write_Byte(0x0E, 0x00) 
        self.Write_Byte(0x0F, 0x00) 
        self.Write_Byte(0x10, 0x00) 
        self.Write_Byte(0x11, 0x00) 
        self.Write_Byte(0x12, 0x00) 
        self.Write_Byte(0x13, 0x60)   
        
    def AS7341_startMeasure(self,mode):
        data=self.Read_Byte(AS7341_CFG_0)
        data = data & (~(1<<4))
        self.Write_Byte(AS7341_CFG_0, data)
        self.AS7341_EnableSpectralMeasure(false)
        self.Write_Byte(0xAF,0x10)
        
        if mode == eF1F4ClearNIR:
            self.F1F4_Clear_NIR()
        elif mode == eF5F8ClearNIR:
            self.F5F8_Clear_NIR()
        self.AS7341_EnableSMUX(true)
        if self.measureMode == eSyns:
            self.AS7341_SetGpioMode(INPUT)
            self.AS7341_Config(eSyns)
        elif self.measureMode == eSpm:
            self.AS7341_Config(eSpm)
        self.AS7341_EnableSpectralMeasure(true)
        if self.measureMode == eSpm:
            while (self.AS7341_MeasureComplete() == false):
                time.sleep(0.1)     
                
    def AS7341_ReadFlickerData(self):
        flicker=0
        data=self.Read_Byte(AS7341_CFG_0)
        data = data & (~(1<<4))
        self.Write_Byte(AS7341_CFG_0,data)
        self.AS7341_EnableSpectralMeasure(false)
        self.Write_Byte(0xAF,0x10)
        self.FDConfig()
        self.AS7341_EnableSMUX(true)
        self.AS7341_EnableSpectralMeasure(true)
        retry = 100
        if(retry == 0): 
            print(' data access error')
        self.AS7341_EnableFlickerDetection(true)
        time.sleep(0.6)
        flicker = self.Read_Byte(AS7341_STATUS)
        self.AS7341_EnableFlickerDetection(false)
        if (flicker == 37):
            flicker=100
        elif (flicker == 40):
            flicker=0
        elif (flicker == 42):
            flicker=120
        elif (flicker == 44):
            flicker=1
        elif (flicker == 45):
            flicker=2        
        else:
            flicker=2
        return flicker
        
    def AS7341_MeasureComplete(self):
        status=self.Read_Byte(AS7341_STATUS_2)
        if (status & 1<<6):
            return true
        else:
            return false
        
    def AS7341_GetchannelData(self,channel):
        channelData = 0x0000
        data0 = self.Read_Byte(AS7341_CH0_DATA_L + channel*2)
        data1 = self.Read_Byte(AS7341_CH0_DATA_H + channel*2)
        channelData = data1
        channalData = (channelData<<8) | data0
        return channalData
        
    def AS7341_ReadSpectralDataOne(self):
        self.channel1 = self.AS7341_GetchannelData(0)
        self.channel2 = self.AS7341_GetchannelData(1)
        self.channel3 = self.AS7341_GetchannelData(2)
        self.channel4 = self.AS7341_GetchannelData(3)
        self.CLEAR = self.AS7341_GetchannelData(4)
        self.NIR = self.AS7341_GetchannelData(5)
    
    def AS7341_ReadSpectralDataTwo(self):
        self.channel5 = self.AS7341_GetchannelData(0)
        self.channel6 = self.AS7341_GetchannelData(1)
        self.channel7 = self.AS7341_GetchannelData(2)
        self.channel8 = self.AS7341_GetchannelData(3)
        self.CLEAR = self.AS7341_GetchannelData(4)
        self.NIR = self.AS7341_GetchannelData(5)        
    
    def AS7341_SetGpioMode(self,mode):
        data=self.Read_Byte(AS7341_GPIO_2)
        if(mode == INPUT):
            data = data | (1<<2) 
        if(mode == OUTPUT):
            data = data & (~(1<<2))
        self.Write_Byte(AS7341_GPIO_2,data)

    def AS7341_ATIME_config(self,value):
        self.Write_Byte(AS7341_ATIME,value)

    def AS7341_ASTEP_config(self,value):
        lowValue = value & 0x00ff
        highValue = value >> 8       
        self.Write_Byte(AS7341_ASTEP_L,lowValue)
        self.Write_Byte(AS7341_ASTEP_H,highValue)       
    
    def AS7341_AGAIN_config(self,value):
        if (value > 10):
            value = 10
        self.Write_Byte(AS7341_CFG_1,value)          
    
    def AS7341_EnableLED(self,flag):
        self.AS7341_SetBank(1)
        data = self.Read_Byte(AS7341_CONFIG)
        data1 = self.Read_Byte(AS7341_LED)
        if(flag == True):
            data = data | 0x08
        else:
            data = data & 0xf7
            data1 = data1 & 0x7f  
            self.Write_Byte(AS7341_LED,data)
        self.Write_Byte(AS7341_CONFIG,data)
        self.AS7341_SetBank(0);   
        
    def AS7341_SetBank(self,addr):
        data = self.Read_Byte(AS7341_CFG_0)
        if addr == 1:
            data = data | (1<<4)
        elif addr == 0:
            data = data & (~(1<<4))
        self.Write_Byte(AS7341_CFG_0,data)
        
    def AS7341_ControlLed(self,LED,current):
        if(current < 1): 
            current = 1
        current -= 1
        if(current > 19): 
            current = 19
        self.AS7341_SetBank(1)   
        data = 0x00
        #data = self.Read_Byte(AS7341_LED)
        if(LED == True):
            data = 0x80 | current
        else:
            data = current
        self.Write_Byte(AS7341_LED,data)
        time.sleep(0.1)
        #data = self.Read_Byte(AS7341_CFG_0)
        #data = data & (~(1<<4));
        #data = self.Read_Byte(AS7341_CFG_0)
        self.AS7341_SetBank(0)      
    
    def AS7341_INTerrupt(self):
        data = self.Read_Byte(AS7341_STATUS_1)
        if(data & 0x80):
            print('Spectral interrupt generation ！\r\n')
        else:
            return 
    
    def AS7341_ClearInterrupt(self):#new---------------------------------------------------------------
        self.Write_Byte(AS7341_STATUS_1,0xff)
    
    def AS7341_EnableSpectralInterrupt(self,flag):
        data = self.Read_Byte(AS7341_INTENAB)
        if(flag == true):
            data = data | (1<<3)
            self.Write_Byte(AS7341_INTENAB,data)
        else:
            data = data & (~(1<<3))
            self.Write_Byte(AS7341_INTENAB,data)
    
    def AS7341_SetInterruptPersistence(self,value):
        data= value
        self.Write_Byte(AS7341_PERS,data)
        data = self.Read_Byte(AS7341_PERS)
        
    def AS7341_SetThreshold(self,lowThre,highThre):
        if(lowThre >= highThre):
            return 
        else: 
            self.Write_Byte(AS7341_SP_TH_L_LSB,lowThre)
            self.Write_Byte(AS7341_SP_TH_L_MSB,lowThre>>8)  
            self.Write_Byte(AS7341_SP_TH_H_LSB,highThre);
            self.Write_Byte(AS7341_SP_TH_H_MSB,highThre>>8)  
            time.sleep(0.02)

    def AS7341_SetSpectralThresholdChannel(self,value):
        self.Write_Byte(AS7341_CFG_12,value)
        
    def AS7341_GetLowThreshold(self):
        data = self.Read_Byte(AS7341_SP_TH_H_LSB)
        data = (self.Read_Byte(AS7341_SP_TH_H_MSB)<<8) | data
        return data     

    def AS7341_SynsINT_sel(self):
        self.Write_Byte(AS7341_CONFIG,0x05)
        
    def AS7341_disableALL(self):
        self.Write_Byte(AS7341_ENABLE ,0x02)