from kazoo.client import KazooClient
from simulation.config.config import ZOOKEEPER_BARRIER_PATH
from simulation.shared.workloads import Workload
from typing import List


def delete_zookeeper_barrier(zk: KazooClient):
    zk._delete_recursive(ZOOKEEPER_BARRIER_PATH)

def delete_zookeeper_queues(zk: KazooClient, workloads: List[Workload]):
    workload: Workload
    for workload in workloads:
        if zk.exists(workload.task.task_name):
            zk._delete_recursive(f"/{workload.task.task_name}")

def reset_zookeeper(zk: KazooClient, workloads: List[Workload]):
    delete_zookeeper_barrier(zk)
    delete_zookeeper_queues(zk, workloads)
