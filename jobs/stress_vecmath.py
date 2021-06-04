import subprocess
from kazoo.client import KazooClient
from kazoo.recipe.barrier import DoubleBarrier
from kazoo.recipe.queue import LockingQueue


NUMBER_OF_TASKS: int = 2
BARRIER_PATH: str = "/barrier"
JOB_NAME: str = "vecmath"
UTF_ENCODING: str = "utf-16"
ZOOKEEEPER_CLIENT_ENDPOINT: str = "zookeeper:2181" # if using dns


def main() -> None:
    """This job will run stress-ng benchmark and wait for commands
    from a Redis queue.
    """

    zk: KazooClient = KazooClient(hosts='10.1.69.15:2181')
    # zk: KazooClient = KazooClient(hosts=ZOOKEEPER_CLIENT_ENDPOINT)

    zk.start()
    if zk.connected:
        print(f"{JOB_NAME} has connected to Zookeeper")

    zk_queue: LockingQueue = LockingQueue(zk, f"/{JOB_NAME}")
    workload_modifier: int = int.from_bytes(zk_queue.get(), byteorder="little")
    zk_queue.consume()

    zk_barrier: DoubleBarrier = DoubleBarrier(
        zk, BARRIER_PATH, NUMBER_OF_TASKS)
    zk_barrier.enter()

    subprocess.check_output(
        ["stress-ng", f"--{JOB_NAME}", "0", "--metrics", "--cpu-ops", str(50000), "-t", "1m"])
    zk_barrier.leave()

if __name__ == '__main__':
    main()
