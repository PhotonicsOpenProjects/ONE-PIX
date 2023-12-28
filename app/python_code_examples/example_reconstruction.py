import os 
import sys
sys.path.append(f'..{os.sep}..')
from core.Reconstruction import Reconstruction

rec=Reconstruction()
rec.data_reconstruction()

filename='test_datacube'
save_path=f'.{os.sep}'
rec.save_reconstructed_image(filename,save_path)