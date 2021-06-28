from simulation.shared.workloads import WORKLOADS, Workload, Task, get_env_vars
from kazoo.client import KazooClient
from kazoo.recipe.queue import LockingQueue
from kazoo.recipe.barrier import DoubleBarrier
from typing import List
import time
from simulation.shared.kube_api import kube_create_stress_job, kube_delete_job
from simulation.shared.zookeeper import reset_zookeeper
from simulation.workload_profiler.stat_logger import StatLogger
from simulation.config.config import (ZOOKEEPER_CLIENT_ENDPOINT, ZOOKEEPER_BARRIER_PATH, PROFILER_MIN_SHARES, PROFILER_MAX_SHARES,
                                      PROFILER_TRIES, PROFILER_SHARE_INCREMENT, SIMULATION_MIN_WORKLOAD, SIMULATION_MAX_WORKLOAD,
                                      SIMULATION_WORKLOAD_INCREMENT, PROFILER_OUTPUT_PATH, SIMULATION_DIR)

CSV_HEADER: List[str] = ["task", "workload_size", "cpu_shares", "duration"]
NUM_TASKS_TUNING: int = 1


class WorkloadProfiler:
    """Profiles runtimes for Workloads under various inputs and resource configurations
    """

    def __init__(self):
        self.stat_logger: StatLogger = StatLogger(
            SIMULATION_DIR + PROFILER_OUTPUT_PATH)
        self.stat_logger.write_header(CSV_HEADER)
        self.zk: KazooClient = KazooClient(hosts=ZOOKEEPER_CLIENT_ENDPOINT)
        self.barrier: DoubleBarrier = DoubleBarrier(
            self.zk, ZOOKEEPER_BARRIER_PATH, NUM_TASKS_TUNING + 1)
        self.zk.start()
        if self.zk.connected:
            print("Resource tuner has connected to Zookeeper")

    def time_workload(self, queue: LockingQueue, workload_size: int) -> float:
        total_duration: float = 0
        for _ in range(PROFILER_TRIES):
            queue.put(bytes([workload_size]))
            self.barrier.enter()
            start: float = time.time()
            self.barrier.leave()
            total_duration += time.time() - start
        return total_duration / PROFILER_TRIES

    def profile_cpu_configuration(self, cpu_shares: int, task: Task) -> None:

        # Create the job
        kube_create_stress_job(get_env_vars(
            task, NUM_TASKS_TUNING), cpu_shares)

        queue: LockingQueue = LockingQueue(self.zk, f"/{task.task_name}")

        workload_size: int
        # print(f"Currently timing job {task.task_name}")
        for workload_size in range(SIMULATION_MIN_WORKLOAD, SIMULATION_MAX_WORKLOAD, SIMULATION_WORKLOAD_INCREMENT):
            duration: float = self.time_workload(queue, workload_size)
            print(
                f"{task.task_name}, {workload_size}, {cpu_shares}, {duration}")
            self.stat_logger.log_statistics(
                [task.task_name, workload_size, cpu_shares, duration])
        kube_delete_job(task.task_name)

    def profile_resource_configurations(self, workloads: List[Workload]) -> None:
        workload: Workload
        cpu_shares: int
        for workload in workloads:
            for cpu_shares in range(PROFILER_MIN_SHARES, PROFILER_MAX_SHARES, PROFILER_SHARE_INCREMENT):
                self.profile_cpu_configuration(cpu_shares, workload.task)
        reset_zookeeper(self.zk, workloads)
        self.stat_logger.close_file()


def main():
    workload_profiler: WorkloadProfiler = WorkloadProfiler()
    workload_profiler.profile_resource_configurations(WORKLOADS)


if __name__ == "__main__":
    main()
