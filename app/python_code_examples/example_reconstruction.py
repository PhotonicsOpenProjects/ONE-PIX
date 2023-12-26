import os 
import sys
sys.path.append(f'..{os.sep}..')
from core.Reconstruction import Reconstruction

rec=Reconstruction()
#rec.load_raw_data()
rec.data_reconstruction()
rec.save_reconstructed_image()