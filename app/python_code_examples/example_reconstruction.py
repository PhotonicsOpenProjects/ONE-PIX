import os 
import sys
sys.path.append(f'..{os.sep}..')
from core import Reconstruction

rec=Reconstruction.Reconstruction()
rec.load_raw_data()
rec.reconstruct()
rec.save_reconstructed_image()