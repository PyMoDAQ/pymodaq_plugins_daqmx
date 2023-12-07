import nidaqmx
from nidaqmx.constants import AcquisitionType,Edge
import time
import matplotlib.pyplot as plt
import time
import numpy as np

task=nidaqmx.Task()
CI_channel = task.ci_channels.add_ci_count_edges_chan("Dev1/ctr0")


print(task.ci_channels.channel_names)
nidaqmx.CtrTime(0.2,0.1)

a=0
b=0
data=[]
task.start()
for i in range(512):
    a=task.read()
    data.append(a)
    print(a)



task.stop()
task.close()
plt.plot(data)
plt.show()