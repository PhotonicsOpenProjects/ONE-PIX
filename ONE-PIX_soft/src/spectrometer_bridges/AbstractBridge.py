# -*- coding: utf-8 -*-
"""
Created on Mon Oct 18 17:47:42 2021

@author: mribes
"""
class AbstractBridge:
   	
    def spec_open(self):
        raise Exception("No implementation provided for spec_open()!")
    
    def set_integration_time(self):
        raise Exception("No implementation provided for set_integration_time()!")
    
    def get_wavelengths(self):
        raise Exception("No implementation provided for get_wavelengths()!")
    
    def get_intensities(self):
        raise Exception("No implementation provided for get_intensities()!")
    
    def spec_close(self):
        raise Exception("No implementation provided for spec_close()!")