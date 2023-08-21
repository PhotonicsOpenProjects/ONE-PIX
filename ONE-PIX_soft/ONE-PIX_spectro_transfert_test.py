# -*- coding: utf-8 -*-
"""
Created on Tue Dec  6 10:47:21 2022

@author: mribes
"""
from src.AcquisitionConfig import *

json_path="./acquisition_param_ONEPIX.json"
config = OPConfig(json_path)

integ_times=np.arange(1,260,5)
rep=64
ech=np.size(integ_times)
t_start=[]
t_end=[]

config.spec_lib.spec_open()
# spectrumX=indigo_get_wl(ser)

for tint in integ_times :
    spectrumData = []
    config.spec_lib.integration_time_ms=tint
    config.spec_lib.set_integration_time()
    
    for k in range(rep):
        t_start.append(time.time())
        spectrumData.append(config.spec_lib.get_intensities())
        t_end.append(time.time())
config.spec_lib.spec_close()

#%% Display
time_start=np.reshape(np.array(t_start),(ech,rep))
time_end=np.reshape(np.array(t_end),(ech,rep))

dt=(time_end-time_start)*1000


plt.figure()
plt.errorbar(integ_times, np.mean(dt,1), yerr=np.std(dt,1)/np.sqrt(rep))
plt.plot(integ_times,integ_times,'*')
plt.legend(['tint','tint+transfert'])
plt.xlabel('Tint échantilloné (ms)')
plt.ylabel('Durées mesurées (ms)')
plt.show()

plt.figure()
plt.errorbar(integ_times, np.mean(dt,1)-integ_times, yerr=np.std(dt,1)/np.sqrt(rep))
plt.xlabel('Tint échantilloné (ms)')
plt.ylabel('Durées de chargement mesurées (ms)')
plt.show()

if (abs(np.mean(np.mean(dt,1)-integ_times))>10):
    print(f'WARNING: YOUR SPECTROMETER DEVICE MAY ACQUIRE OR TRANSFERT SPECTRA TOO SLOWLY.\
          CONSIDER USING ANOTHER SPECTROMETER FOR FAST MEASUREMENTS OR BE SURE THAT PATTERNS\
              DISPLAY TIME IS STRICTLY SUPERIOR TO {abs(np.mean(np.mean(dt,1)-integ_times))} ms' )
else :
    print("Your spectrometer is fast enough to acquire hypercubes with the ONE-PIX kit")