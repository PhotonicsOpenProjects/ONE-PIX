class Analysis:

    def __init__(self,rec=None):

        if rec is None:
            self.load_reconstruct_image()
            
        else:
            self.imaging_method=rec.imaging_method
            self.reconstruct_image=rec.imaging_method.reconstructed_image


    def load_reconstruct_image(self):
        self.read_hader()
        self.imaging_method.analysis.load_image()
        return 
    

    def plot_image(self):
        self.imaging_method.analysis.plot_reconstruct_image() 


