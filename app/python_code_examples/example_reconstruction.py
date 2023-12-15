import os 
import sys
actual_path=os.getcwd()
os.chdir("..")
os.chdir("..")
root_path=os.getcwd()
os.chdir(actual_path)
sys.path.insert(0, root_path)
from core import Reconstruction 

rec=Reconstruction.Reconstruction()
rec.load_raw_data()
rec.reconstruct