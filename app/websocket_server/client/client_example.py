
from onepix_client import OnePixClient
import matplotlib.pyplot as plt 



client = OnePixClient("http://localhost:5000")
client.connect()

client.change_param("imaging_method", "FourierSplit")
client.change_param("integration_time_ms", "2")
spectro_scans2avg = client.read_param("spectro_scans2avg")

result = client.run_measure()
client.disconnect()


wl=result["wavelengths"]
datacube=result['hypercube']
rgb_img=result["rgb_img"]

plt.figure()
plt.imshow(rgb_img)
plt.show()


