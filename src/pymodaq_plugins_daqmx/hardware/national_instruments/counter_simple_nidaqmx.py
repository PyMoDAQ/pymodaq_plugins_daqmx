import nidaqmx
import numpy as np
import time

# Constantes équivalentes aux macros en C
DAQmx_Val_Rising = nidaqmx.constants.Edge.RISING
DAQmx_Val_CountUp = nidaqmx.constants.CountDirection.COUNT_UP

def main():
    error = 0
    task_handle = nidaqmx.Task()
    data = np.zeros(1, dtype=np.uint32)

    try:
        # DAQmx Configure Code
        task_handle.ci_channels.add_ci_count_edges_chan("Dev1/ctr0", edge=DAQmx_Val_Rising, initial_count=0, count_direction=DAQmx_Val_CountUp)

        # DAQmx Start Code
        task_handle.start()

        print("En cours de lecture en continu. Appuyez sur Ctrl+C pour interrompre\n")
        while True:
            # DAQmx Read Code
            data=task_handle.read(number_of_samples_per_channel=1)

            print("\rCompteur : {}".format(data[0]), end='', flush=True)
            time.sleep(0.1)  # Intervalle pour éviter une utilisation excessive du processeur

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
