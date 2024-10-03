import ONEPIX2Spyrit_library as co
import numpy as np 
import matplotlib.pyplot as plt

conv=co.onepix2spyrit()
conv_linear=co.onepix2spyrit()

conv.load_onepix_mes()
# conv_linear.load_onepix_mes()

conv.onepix2spyrit_mes()

conv.linear_hadam_spyrit_reconstruct()
false_rgb_img_linear=conv.RGB_reconstruction(conv.datacube,conv.onepix_mes['wavelengths'])
conv.cnn32to64_hadam_spyrit_reconstruct()
false_rgb_img_cnn=conv.RGB_reconstruction(conv.datacube,conv.onepix_mes['wavelengths'])

plt.figure()
plt.subplot(121)
plt.title("linear reconstruction")
plt.imshow(false_rgb_img_linear)
plt.subplot(122)
plt.imshow(false_rgb_img_cnn)
plt.title("cnn reconstruction")
plt.show()


# print(datacube.shape)

# plt.figure()
# plt.imshow(datacube[:,:,600])
# plt.show()


