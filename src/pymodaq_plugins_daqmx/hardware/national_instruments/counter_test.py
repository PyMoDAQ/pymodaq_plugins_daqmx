import PyDAQmx
import ctypes
import numpy as np


counter_input = PyDAQmx.Task()
read = PyDAQmx.int32()
data = np.zeros((1000,),dtype=np.float64)

#DAQmx Configure Code
counter_input.CreateCICountEdgesChan("Dev1/ctr0","",PyDAQmx.DAQmx_Val_Rising,0,PyDAQmx.DAQmx_Val_CountUp)

#DAQmx Start Code
counter_input.StartTask()

#DAQmx Read Code
counter_input.ReadCounterScalarU32(10.0,PyDAQmx.byref(data),None)

print(read.value)