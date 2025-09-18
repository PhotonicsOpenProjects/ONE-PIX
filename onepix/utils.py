import numpy as np

def to_serializable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()  
    return str(obj)  


def default(obj):
    return to_serializable(obj)  # ton convertisseur numpy → list