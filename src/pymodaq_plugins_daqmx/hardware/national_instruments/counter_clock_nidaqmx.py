import nidaqmx
import numpy as np
from nidaqmx.constants import Edge, AcquisitionType, FillMode, LineGrouping, CountDirection
from nidaqmx.stream_readers import CounterReader
from ctypes import c_uint32

def main():
    error = 0
    task_handle = nidaqmx.Task()
    data = np.zeros(0, dtype=np.uint32)
    read = np.uint32()

    try:
        # DAQmx Configure Code
        task_handle.ci_channels.add_ci_count_edges_chan("Dev1/ctr0", edge=Edge.RISING, initial_count=0, count_direction=CountDirection.COUNT_UP)
        task_handle.timing.cfg_samp_clk_timing(source="/Dev1/Ctr1InternalOutput", rate=1000.0, active_edge=Edge.RISING, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000)

        counter_reader=CounterReader(task_handle.in_stream)
        # DAQmx Start Code
        task_handle.start()

        print("En cours de lecture en continu. Appuyez sur Ctrl+C pour interrompre\n")
        while True:
            # DAQmx Read Code
            #data=task_handle.read(number_of_samples_per_channel=1000, timeout=10.0)
            #task_handle.in_stream.read_all_avail_samp
            read=counter_reader.read_many_sample_uint32(data)
            print("\rAcquis {} échantillons".format(read), end='', flush=True)

    except Exception as e:
        print("\n")
        if task_handle.is_task_done() == 0:
            task_handle.stop()
            task_handle.close()
        print("Erreur DAQmx : {}".format(str(e)))

    finally:
        print("\nFin du programme. Appuyez sur la touche Entrée pour quitter\n")
        input()

if __name__ == "__main__":
    main()
