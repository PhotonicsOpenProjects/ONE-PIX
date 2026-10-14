import PicameraBridge as pi
import matplotlib.pyplot as plt 

cam=pi.PicameraBridge()
cam. init_camera()
img_test=cam.get_image_var()
cam.close()

plt.figure()
plt.imshow(img_test)
plt.show()


