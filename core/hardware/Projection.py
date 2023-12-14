import importlib
import cv2


screenWidth = screeninfo.get_monitors()[0].width
try:
    proj_shape=screeninfo.get_monitors()[1]
except IndexError:
    print('Please use a projector to use ONE-PIX')
    #sys.exit()


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
    
    def reshape_patterns(self,patterns):

        if self.pattern_method in self.seq_basis: # Method used to create, display and measure sequentially patterns within a specific basis
            pattern_reduction=[4,3]
            # horizontal vector for the pattern creation
            x = np.arange(0,self.width//pattern_reduction[0],dtype=np.uint8)
            # vertical vector for the pattern creation
            y = np.arange(0,self.height//pattern_reduction[1],dtype=np.uint8)
            # horizontal and vertical array for the pattern creation
            Y, X = np.meshgrid(x, y)
    
            self.pattern_order, freqs = self.pattern_lib.decorator.sequence_order() # Get spatial frequencies list to create patterns
            self.interp_method=cv2.INTER_LINEAR_EXACT
            
            for freq in freqs:
                self.pattern_lib.decorator.sequence.extend(self.pattern_lib.decorator.creation_patterns(X, Y, freq))  # Patterns creations 
            
        elif self.pattern_method in self.full_basis:
            self.pattern_order,freq=self.pattern_lib.decorator.creation_patterns()
            self.interp_method=cv2.INTER_AREA
        self.nb_patterns=self.pattern_lib.nb_patterns=len(self.pattern_lib.decorator.sequence)
        print(f"sequence of {self.pattern_lib.nb_patterns} is ready !")

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

    def init_projection_windows(self):
                # Initialise cv2 display on the second monitor 
        cv2.namedWindow('ImageWindow', cv2.WINDOW_NORMAL)
        cv2.moveWindow('ImageWindow', screenWidth, 0)
        cv2.setWindowProperty("ImageWindow", cv2.WND_PROP_FULLSCREEN, 1)
        cv2.imshow('ImageWindow',cv2.resize(self.pattern_lib.decorator.sequence[0],(self.width,self.height),interpolation=self.interp_method))
        cv2.waitKey(750) # allows the projector to take the time to display the first pattern, particularly if it is white     

        def thread_projection(self,event):
        """
        This function allows to display a sequence of patterns.
       
        Parameters
        ----------
        event : threading Event 
            Ensures the synchronisation between displays and measures
        config : class
            OPConfig class object.
    
        Returns
        -------
        None.
    
        """  
        hardware.projection.init_projection_windows()         
        try:
            white_idx=self.pattern_lib.decorator.white_pattern_idx
        except:           
            white_idx=-100
        delta_idx=4 if self.pattern_method=='FourierSplit' else 2
        # Display each pattern from the sequence
        for count,pattern in enumerate(self.pattern_lib.decorator.sequence):
            if  count in np.arange(white_idx,white_idx+delta_idx):
                self.spectro_flag=True
           

            cv2.imshow('ImageWindow',cv2.resize(pattern,(self.width,self.height),interpolation=self.interp_method))
            cv2.waitKey(int(self.periode_pattern))
            event.set()
            time.sleep(1e-6)
            while event.is_set():
                time.sleep(1e-6)
            

        cv2.destroyAllWindows()
