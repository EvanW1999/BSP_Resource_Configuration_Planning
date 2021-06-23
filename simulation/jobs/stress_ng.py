import subprocess
import os
from kazoo.client import KazooClient
from kazoo.recipe.barrier import DoubleBarrier
from kazoo.recipe.queue import LockingQueue
from simulation.shared.env_vars import EnvVarName

NUM_TASKS: int = int(os.getenv(EnvVarName.NUM_TASKS.value, 1))
JOB_NAME: str = os.getenv(EnvVarName.JOB_NAME.value, "TestJob")
OP_NAME: str = os.getenv(EnvVarName.OP_NAME.value, "TestOp")
WORKLOAD_MODIFIER: int = int(os.getenv(EnvVarName.WORKLOAD_MODIFIER.value, 10))
NUM_INSTANCES: int = int(os.getenv(EnvVarName.NUM_INSTANCES.value, 0))
ZOOKEEPER_CLIENT_ENDPOINT: str = os.getenv(
    EnvVarName.ZOOKEEPER_CLIENT_ENDPOINT.value, "zookeeper:2181")
BARRIER_PATH: str = os.getenv(EnvVarName.BARRIER_PATH.value, "/barrier")


STRESS_NG_COMMAND: str = "stress-ng"


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
        zk_barrier.enter()
        print(f"Starting with workload: {workload}")
        subprocess.check_output(
            [STRESS_NG_COMMAND, "--metrics", f"--{JOB_NAME}", str(NUM_INSTANCES), OP_NAME, str(WORKLOAD_MODIFIER * workload)])
        zk_barrier.leave()


if __name__ == '__main__':
    main()
