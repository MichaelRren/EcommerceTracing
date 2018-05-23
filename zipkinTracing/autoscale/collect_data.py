import time
import numpy as np
#import matplotlib.pyplot as plt
from multiprocessing import Pool
import subprocess

from domonit.containers import Containers
from domonit.ids import Ids
from domonit.inspect import Inspect
from domonit.logs import Logs
from domonit.process import Process
from domonit.changes import Changes
from domonit.stats import Stats
#from latency_tracking import getLatency
from query_latency import queryLatency

LOOKBACK = 3500
SERVICE_NAME = "orders"
HOST_IP = "128.253.128.66"
TIME_LIMIT = 8 * 60 # 5 minutes
MEMORY_SWAP_ERROR = "Memory limit should be smaller than already set memoryswap limit, update the memoryswap at the same time"
SCALE_TIMES = []

def scale_up():
    containers = Containers()
    ids = Ids()

    print("SCALING UP")
    for container_id in ids.ids():
        ins = Inspect(container_id)
        sta = Stats(container_id)
        prc = Process(container_id, ps_args="aux")

        mem_u = sta.memory_stats_usage()
        mem_l = sta.memory_stats_limit()
        mem_usage = int(mem_u) / int(mem_l)
        print("MEM USAGE", mem_usage)

        if mem_usage >= 0.8:
            print("SCALING UP", container_id)
            new_limit = int(mem_l) * 1.66
            update_process = subprocess.Popen(['docker', 'update', '--memory', str(new_limit), container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            update_process.wait()
            print("SCALED", update_process.returncode, update_process.stderr.read(), update_process.stdout.read())

            if update_process.returncode != 0:
                print("FAILED TO SCALE", container_id)
                update_process = subprocess.Popen(['docker', 'update', '--memory-swap', str(new_limit), '--memory', str(new_limit), container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                update_process.wait()
                print("SCALED2", update_process.returncode, update_process.stderr.read(), update_process.stdout.read())
            else:
                print("SCALED UP", container_id)

def run_scaling(sensitivity, use_utilization=True, use_latency=True):
    assert (use_utilization or use_latency)

    times = []
    latencies = []

    workers = Pool()

    start_ts = int(time.time())
    curr_ts = start_ts

    with Pool() as workers:
        if use_latency:
            while curr_ts - start_ts < TIME_LIMIT:
                curr_ts = int(time.time())
                latency = queryLatency(HOST_IP, SERVICE_NAME, LOOKBACK, True)
                print(latency)

                time_diff = curr_ts - start_ts
                SCALE_TIMES.append(time_diff)
                scale_up()
                workers.apply_async(scale_up)

#            times.append(curr_ts - start_ts)
            latencies.append([time_diff, latency])
            print(str(curr_ts - start_ts) + " s: " + str(latency) + " ms")
            time.sleep(1)

        #workers.join()

    #times = np.array(times)
    latencies = np.array(latencies)
    sort_indices = latencies[:, 0].argsort()
    latencies = latencies[sort_indices]
    #np.savetxt('times', times)
    np.savetxt('latencies', latencies)
#    plt.plot(times, latencies)
 #   plt.show()

if __name__ == "__main__":
    run_scaling(500)
