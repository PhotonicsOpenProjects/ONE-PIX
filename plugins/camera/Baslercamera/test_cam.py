# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 14:52:05 2025

@author: luguen
"""

import BaslercameraBridge as cam

bas = cam.BaslerCameraBridge()
bas.init_camera()
bas.image_capture("init", None)