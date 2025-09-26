import os
import numpy as np
from datetime import date
import time
import json
import logging
from onepix.logging_config import root  
logger = logging.getLogger(__name__)

class FisCommonAcquisition:
    def __init__(self,acquisition_class=None):
        if acquisition_class:
            self.acquisition_class = acquisition_class
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        self.imaging_config_path = os.path.join(base_path, "FIS_common_param.json")
        self.hardware_dict = self._load_json(self.imaging_config_path)
        self.spatial_res=self.hardware_dict["spatial_res"]
        print("in common acquisition spatial res is ",self.spatial_res)

    @staticmethod
    def _load_json(path):
        """Charge un fichier JSON en gérant les erreurs."""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"⚠️ Warning: {path} not found. Using empty config.")
            return {}
        

        
        


