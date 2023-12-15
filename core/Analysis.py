class Analysis:

    def __init__(self,rec=rec):

        if rec:
            self.imaging_method=rec.imaging_method
            self.reconstruct_image=rec.reconstruct_image()
        else :
            self.load_reconstruct_image()
            

    def load_reconstruct_image(self):
        self.read_hader()
        self.imaging_method.analysis.load_image()
        return 
    

    def plot_image(self)

        self.imaging_method.analysis.plot_reconstruct_image() 


