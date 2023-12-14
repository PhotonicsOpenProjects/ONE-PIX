import Projection as Proj

class hardware:

    def __init__(self):
        self.harware_config_path="./conf/hardware_config.json"

         ## get hardware configuration
        f = open(self.harware_config_path)
        hardware_dict = json.load(f)
        f.close()

        self.name_spectro = hardware_dict["name_spectro"]
        self.name_camera=hardware_dict["name_spectro"]

        self.proj=Proj.Projection()


        
        self.acquisition_parameter_path="./conf/acquisition_parameter.json"





