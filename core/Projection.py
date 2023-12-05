import importlib


class Projection:
    """
     Allows to build a generic bridge based on a concrete one. Concrete 
     bridge provides correct implementation regarding spectrometer model
     use. The generic bridge is an abstract layer that wrap concrete implementation.
    
     :param str spectro_name:
    		Spectrometer concrete bridge implementation:
    		
     :param float integration_time_ms:
    		spectrometer integration time in milliseconds.
    """
    
    def __init__(self):
        return
    
    
    def OP_init(self):
        """
        This functions allows to display one Fourier pattern and then adapt and
        set the spectrometer's integration time within the OPConfig class.
    
        Parameters
        ----------
        config : class
            OPConfig class object.
    
        Returns
        -------
        config : class
            actualised OPConfig class object.
    
        """ 
        if self.spec_lib.DeviceName=='':
            self.spec_lib.spec_open()
            self.spec_lib.DeviceName=self.spec_lib.decorator.DeviceName
    
        # create static pattern to be displayed
        proj = ctk.CTkToplevel()
        proj.geometry("{}x{}+{}+{}".format(self.width, self.height, screenWidth, 0))
        y = list(range(self.height))  # horizontal vector for the pattern creation
        x = list(range(self.width))  # vertical vector for the pattern creation
        Y, X = np.meshgrid(x, y)  # horizontal and vertical array for the pattern creation
        A = 2 * np.pi * X * 10 / self.height
        B = 2 * np.pi * Y * 10 / self.width
        test_pattern = np.cos(A + B)  # gray pattern creation
        test_pattern[test_pattern < 0] = 0
        #test_pattern=np.ones((self.height,self.width),dtype=np.uint8)
        pil_img = PIL.Image.fromarray(255 * test_pattern)

        img = PIL.ImageTk.PhotoImage(master=proj, image=pil_img)
        label_test_proj = Label(proj, image=img)
        label_test_proj.image = img
        label_test_proj.pack()

        proj.update()
        time.sleep(0.5)
        
        print('Finding the optimal integration time (ms):')
        self.get_optimal_integration_time()
        proj.destroy()
        self.periode_pattern=int(self.rep*self.integration_time_ms)
        if self.periode_pattern<60 :self.periode_pattern=60