import nidaqmx
from nidaqmx.constants import AcquisitionType,Edge
import time
import matplotlib.pyplot as plt

task=nidaqmx.Task()
task.ci_channels.add_ci_count_edges_chan("Dev1/ctr0")


task.start()
data=task.read(512)
#for i in range(512):
#    mesure0 = task.read()
#    data.append(task.read()-mesure0)
task.stop()

print(data)
task.close()
plt.plot(data)
plt.show()