import sys
import importlib
from src.patterns_bases.AbstractBasis import AbstractBasis


class PatternMethodSelection:
    """
     Allows to build a generic bridge based on a concrete one. Concrete 
     bridge provides correct implementation regarding to pattern bases model 
     use. The generic bridge is an abstract layer that wrap concrete implementation.

     :param str pattern_method:
    		ONE-PIX pattern method to invoke one specific class of patterns.
    		~~~~
     :param int spatial_res:
    		Spatial resolution of the datacube to be acquired.
            ~~~~
     :param int height:
    		number of pixels for the raws of patterns.
            ~~~~
     :param int width:
    		number of pixels for the column of patterns.
    """
    
    def __init__(self,pattern_method,spatial_res,height,width):
        
        # Concrete spectrum implementation dynamic instanciation
        try:
            # module = pattern_method.split('.')
            # className = module[-1]
            # module = '.'.join(module[0:len(module)-1])
            # module = importlib.import_module(module)
            module='src.pattern_bases'
            className=pattern_method+'Patterns'
            module=importlib.import_module('src.patterns_bases.'+pattern_method+'Patterns')
            classObj = getattr(module, className)
            self.decorator = classObj(spatial_res)
        except:
            raise Exception("Concrete bridge \"" + pattern_method + "\" implementation has not been found.")
        # if not isinstance(self.decorator, AbstractBasis):
        #     raise Exception("Concrete bridge \"" + pattern_method + "\" must implement class bridges.AbstractBridge.")

        self.method=pattern_method
        self.spatial_res=spatial_res
        self.height=height
        self.width=width
        self.nb_patterns=self.decorator.nb_patterns
        self.dim=0
        
        # if(self.method=='Custom'):
        #     self.decorator.creation_patterns()
        
    # def sequence_order(self):
    #    return self.decorator.sequence_order
    
    # def creation_patterns(self):
    #     return self.decorator.creation_patterns
   

    
    
           
            
        
    
        
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
    
    