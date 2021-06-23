import numpy
import time
from abc import ABC, abstractmethod
from kazoo.client import KazooClient
from kazoo.recipe.queue import LockingQueue
from kazoo.recipe.barrier import DoubleBarrier
from numpy.core.einsumfunc import _compute_size_by_dict
from simulation.shared.zookeeper import reset_zookeeper
from simulation.shared.kube_api import kube_create_stress_job, kube_delete_job
from simulation.config.config import GANG_SCHEDULING_CHECKPOINT_PENALTY, ZOOKEEPER_CLIENT_ENDPOINT, ZOOKEEPER_BARRIER_PATH, GANG_SCHEDULING_SIMULATION_LENGTH
from simulation.shared.workloads import WORKLOADS, Workload, get_env_vars
from simulation.forecaster.lstm_forecaster import get_actual_dict, get_predictions_dict
from simulation.gang_scheduling.mpc import MPController, StaticMPController
from simulation.gang_scheduling.resource_configurer import ResourceConfigurer, ConfigurationWindow
from typing import Dict, List


class Simulator(ABC):
    """
    This class simulates a gang-scheduling experiment
    """

    def __init__(self,
                 resource_configurer: ResourceConfigurer,
                 workloads: List[Workload],
                 actual: Dict[str, numpy.ndarray],
                 predicted: Dict[str, numpy.ndarray],
                 zookeeper_client_endpoint: str,
                 zookeeper_barrier_path: str):

        self.resource_configurer = resource_configurer
        self.workloads = workloads
        self.actual = actual
        self.predicted = predicted
        self.zk = KazooClient(hosts=zookeeper_client_endpoint)
        self.zk.start()

        if self.zk.connected:
            print("Simulator has connected to Zookeeper")

        self.zk_barrier = DoubleBarrier(
            self.zk, zookeeper_barrier_path, len(self.workloads) + 1)
        self.zk_queues: Dict[str, LockingQueue] = {
            workload.task.task_name: LockingQueue(self.zk, f"{workload.task.task_name}") for workload in self.workloads
        }

    def create_workloads_from_configuration(self, configuration: Dict[str, int]) -> None:
        workload: Workload
        for workload in self.workloads:
            kube_create_stress_job(env_vars=get_env_vars(
                task=workload.task, num_tasks=len(self.workloads)), cpu_shares=configuration[workload.task.task_name])

    def delete_jobs(self) -> None:
        for workload in self.workloads:
            kube_delete_job(workload.task.task_name)

    def simulate_timestep(self, time_step: int) -> float:
        for workload_name, workload_size in self.actual.items():
            self.zk_queues[workload_name].put(
                bytes([round(workload_size[time_step][0])])
            )
        self.zk_barrier.enter()
        start: float = time.time()
        self.zk_barrier.leave()
        duration: float = time.time() - start
        print(
            f"Simulation timestep {time_step} has finished with duration {duration}")
        return duration

    @abstractmethod
    def simulate(self) -> float:
        """
        Simulate a gang scheduling experiment

        Returns:
            float: Duration of the experiment
        """
        pass


class StaticSimulator(Simulator):

    def __init__(self,
                 resource_configurer: ResourceConfigurer,
                 workloads: List[Workload],
                 actual: Dict[str, numpy.ndarray],
                 predicted: Dict[str, numpy.ndarray],
                 zookeeper_client_endpoint: str,
                 zookeeper_barrier_path: str):

        super().__init__(resource_configurer=resource_configurer,
                         workloads=workloads,
                         actual=actual,
                         predicted=predicted,
                         zookeeper_client_endpoint=zookeeper_client_endpoint,
                         zookeeper_barrier_path=zookeeper_barrier_path)

    def simulate(self) -> float:
        time_step: int
        resource_configuration: Dict[str,
                                     int] = self.resource_configurer.calculate_static_configuration()
        self.create_workloads_from_configuration(resource_configuration)
        total_duration: float = 0
        for time_step in range(GANG_SCHEDULING_SIMULATION_LENGTH):
            total_duration += self.simulate_timestep(time_step)
        self.delete_jobs()
        print(f"Simulation took {total_duration} total seconds")
        return total_duration


class MPCSimulator(Simulator):

    def __init__(self,
                 mpc: MPController,
                 resource_configurer: ResourceConfigurer,
                 workloads: List[Workload],
                 actual: Dict[str, numpy.ndarray],
                 predicted: Dict[str, numpy.ndarray],
                 zookeeper_client_endpoint: str,
                 zookeeper_barrier_path: str):

        super().__init__(resource_configurer=resource_configurer,
                         workloads=workloads,
                         actual=actual,
                         predicted=predicted,
                         zookeeper_client_endpoint=zookeeper_client_endpoint,
                         zookeeper_barrier_path=zookeeper_barrier_path)
        self.mpc = mpc
        self.current_config: Dict[str, int] = {}

    def create_new_configuration_from_window(self, time_step: int, window_size: int) -> None:
        print(f"Creating configuration for window size of {window_size}")
        new_configuration = self.resource_configurer.calculate_resource_configurations(
            ConfigurationWindow(
                simulation_time_step=time_step,
                window_size=window_size,
                starting_prediction=0
            )
        )
        print(new_configuration)
        if time_step != 0:
            self.delete_jobs()
        self.create_workloads_from_configuration(new_configuration)
        self.current_config = new_configuration

    def simulate(self) -> float:
        time_step: int
        total_duration: float = 0
        num_checkpoints: int = 0
        for time_step in range(GANG_SCHEDULING_SIMULATION_LENGTH):
            window_size = self.mpc.calculate_time_horizon(
                time_step, self.current_config)
            if window_size != 0:
                self.create_new_configuration_from_window(
                    time_step, window_size)
                num_checkpoints += int(time_step != 0)
            total_duration += self.simulate_timestep(time_step)

        self.delete_jobs()
        print(
            f"Simulation took {total_duration} total seconds, with {num_checkpoints} Checkpoints")
        print(
            f"With checkpoints, the total duration would be {total_duration + GANG_SCHEDULING_CHECKPOINT_PENALTY * num_checkpoints}")
        return total_duration


def main() -> None:

    predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    actual: Dict[str, numpy.ndarray] = get_actual_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        workloads=WORKLOADS, predictions=actual)
    print(resource_configurer.calculate_static_configuration())

    # static_simulator: StaticSimulator = StaticSimulator(
    #     resource_configurer=resource_configurer,
    #     workloads=WORKLOADS,
    #     actual=actual,
    #     zookeeper_client_endpoint=ZOOKEEPER_CLIENT_ENDPOINT,
    #     zookeeper_barrier_path=ZOOKEEPER_BARRIER_PATH)
    # static_simulator.simulate()
    static_mpc: StaticMPController = StaticMPController(
        resource_configurer=resource_configurer,
        static_window_size=2
    )
    mpc_simulator: MPCSimulator = MPCSimulator(
        mpc=static_mpc,
        resource_configurer=resource_configurer,
        workloads=WORKLOADS,
        actual=actual,
        predicted=actual,
        zookeeper_client_endpoint=ZOOKEEPER_CLIENT_ENDPOINT,
        zookeeper_barrier_path=ZOOKEEPER_BARRIER_PATH
    )
    mpc_simulator.simulate()


if __name__ == "__main__":
    main()
