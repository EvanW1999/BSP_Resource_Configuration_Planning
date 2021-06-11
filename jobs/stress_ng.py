import subprocess
import os
from kazoo.client import KazooClient
from kazoo.recipe.barrier import DoubleBarrier
from kazoo.recipe.queue import LockingQueue


NUM_TASKS: int = int(os.getenv("NUM_TASKS", 1))
JOB_NAME: str = os.getenv("JOB_NAME", "matrix")
OP_NAME: str = os.getenv("OP_NAME", "cpu-ops")

ZOOKEEPER_CLIENT_ENDPOINT: str = "zookeeper:2181"  # if using dns
BARRIER_PATH: str = "/barrier"


def main() -> None:
    """This job will run stress-ng benchmark and wait for commands
    from a Redis queue.
    """

    zk: KazooClient = KazooClient(hosts=ZOOKEEPER_CLIENT_ENDPOINT)
    zk.start()

    if zk.connected:
        print(f"{JOB_NAME} has connected to Zookeeper")

    zk_queue: LockingQueue = LockingQueue(zk, f"/{JOB_NAME}")
    zk_barrier: DoubleBarrier = DoubleBarrier(
        zk, BARRIER_PATH, NUM_TASKS + 1)

    while True:
        print("Job is ready")
        workload: int = int.from_bytes(zk_queue.get(), byteorder="little")
        zk_queue.consume()

        if workload == 255:
            break

        zk_barrier.enter()
        print(f"Starting with workload: {workload}")
        subprocess.check_output(
            ["stress-ng", f"--{JOB_NAME}", "0", f"--{OP_NAME}", str(20000 * workload)])
        zk_barrier.leave()


if __name__ == '__main__':
    main()
