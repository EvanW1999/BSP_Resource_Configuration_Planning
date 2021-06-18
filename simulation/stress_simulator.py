from kazoo.client import KazooClient
from kazoo.recipe.queue import LockingQueue
from kazoo.recipe.barrier import DoubleBarrier
from simulation.shared.create_kube_job import kube_create_job, kube_update_job, kube_delete_job
from simulation.shared.zookeeper import reset_zookeeper
from simulation.config.config import ZOOKEEPER_CLIENT_ENDPOINT, ZOOKEEPER_BARRIER_PATH
from typing import Dict, List


JOB_NAMES: List[str] = ["matrix", "vecmath"]
NUM_TASKS: int = len(JOB_NAMES)
WORKLOADS: List[int] = [5, 5, 255]


def main() -> None:
    env_vars: Dict[str, str] = {
        "NUM_TASKS": str(NUM_TASKS), "OP_NAME": "cpu-ops", "PYTHONUNBUFFERED": "1"}

    zk: KazooClient = KazooClient(hosts=ZOOKEEPER_CLIENT_ENDPOINT)
    zk.start()

    if zk.connected:
        print("Simulator has connected to Zookeeper")

    print(zk.get_children("/"))

    zk_barrier: DoubleBarrier = DoubleBarrier(
        zk, ZOOKEEPER_BARRIER_PATH, NUM_TASKS + 1)

    job_name: str
    zk_queues: Dict[str, LockingQueue] = {}
    for job_name in JOB_NAMES:
        env_vars["JOB_NAME"] = job_name
        kube_create_job(env_vars, 6000)
        zk_queues[job_name] = LockingQueue(zk, f"/{job_name}")

    workload: int
    print("Jobs Created")
    for workload in WORKLOADS:
        for job_name in JOB_NAMES:
            zk_queues[job_name].put(bytes([workload]))
        if workload != 255:
            zk_barrier.enter()
            zk_barrier.leave()

    for job_name in JOB_NAMES:
        env_vars["JOB_NAME"] = job_name
        kube_update_job(env_vars, 5000)

    for workload in WORKLOADS:
        for job_name in JOB_NAMES:
            zk_queues[job_name].put(bytes([workload]))
        if workload != 255:
            zk_barrier.enter()
            zk_barrier.leave()

    for job_name in JOB_NAMES:
        kube_delete_job(job_name)
    print("Jobs Finished")
    reset_zookeeper(zk, WORKLOADS)


if __name__ == "__main__":
    main()
