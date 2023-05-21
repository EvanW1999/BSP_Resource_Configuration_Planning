from typing import Dict, List
import numpy
import time
from abc import ABC, abstractmethod
from kazoo.client import KazooClient
from kazoo.recipe.queue import LockingQueue
from kazoo.recipe.barrier import DoubleBarrier

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))


from simulation.gang_scheduling.resource_configurer import ResourceConfigurer, ConfigurationWindow
from simulation.gang_scheduling.mpc import DynamicMPController, MPController, StaticMPController
from simulation.forecaster.lstm_forecaster import get_actual_dict, get_predictions_dict
from simulation.shared.workloads import WORKLOADS, Workload, get_env_vars
from simulation.config.config import (GANG_SCHEDULING_CHECKPOINT_PENALTY, GANG_SCHEDULING_STARTING_SHARES, ZOOKEEPER_CLIENT_ENDPOINT,
                                      ZOOKEEPER_BARRIER_PATH, GANG_SCHEDULING_SIMULATION_LENGTH, GANG_SCHEDULING_WINDOW_SIZE)
from simulation.shared.kube_api import kube_create_stress_job, kube_delete_job
from simulation.shared.zookeeper import reset_zookeeper


class Simulator(ABC):
    """
    This class simulates a gang-scheduling experiment
    """

    def __init__(self,
                 resource_configurer: ResourceConfigurer,
                 workloads: List[Workload],
                 actual: Dict[str, numpy.ndarray],
                 zookeeper_client_endpoint: str,
                 zookeeper_barrier_path: str,
                 real_simulation: bool):

        self.resource_configurer = resource_configurer
        self.workloads = workloads
        self.actual = actual
        self.real_simulation = real_simulation
        if self.real_simulation:
            self.zk = KazooClient(hosts=zookeeper_client_endpoint)
            self.zk.start()
            if self.zk.connected:
                print("Simulator has connected to Zookeeper")
            self.zk_barrier = DoubleBarrier(
                self.zk, zookeeper_barrier_path, len(self.workloads) + 1)
            self.zk_queues: Dict[str, LockingQueue] = {
                workload.task.task_name: LockingQueue(self.zk, f"{workload.task.task_name}") for workload in self.workloads
            }

        else:
            self.fake_resource_configurer = ResourceConfigurer(
                workloads=workloads,
                predictions=actual
            )

        self.current_config: Dict[str, int] = {
            workload.task.task_name: GANG_SCHEDULING_STARTING_SHARES for workload in self.workloads}

    def create_workloads_from_configuration(self, configuration: Dict[str, int]) -> None:
        workload: Workload
        for workload in self.workloads:
            kube_create_stress_job(env_vars=get_env_vars(
                task=workload.task, num_tasks=len(self.workloads)), cpu_shares=configuration[workload.task.task_name])

    def delete_jobs(self) -> None:
        for workload in self.workloads:
            kube_delete_job(workload.task.task_name)
        reset_zookeeper(self.zk, self.workloads)

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

    def fake_simulate_timestep(self, time_step: int) -> float:
        return self.fake_resource_configurer.calculate_estimated_runtime(
            self.current_config,
            ConfigurationWindow(
                simulation_time_step=time_step,
                window_size=1,
                starting_prediction=0
            )
        )

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
                 zookeeper_client_endpoint: str,
                 zookeeper_barrier_path: str,
                 real_simulation: bool):

        super().__init__(resource_configurer=resource_configurer,
                         workloads=workloads,
                         actual=actual,
                         zookeeper_client_endpoint=zookeeper_client_endpoint,
                         zookeeper_barrier_path=zookeeper_barrier_path,
                         real_simulation=real_simulation)

    def simulate(self) -> float:
        time_step: int
        self.current_config: Dict[str,
                                  int] = self.resource_configurer.calculate_static_configuration()
        if self.real_simulation:
            self.create_workloads_from_configuration(self.current_config)
        total_duration: float = 0
        for time_step in range(GANG_SCHEDULING_SIMULATION_LENGTH):
            duration: float = self.simulate_timestep(
                time_step) if self.real_simulation else self.fake_simulate_timestep(time_step)
            # print(duration)
            total_duration += duration
        if self.real_simulation:
            self.delete_jobs()
        print(f"Static simulation took {total_duration} total seconds")
        return total_duration


class MPCSimulator(Simulator):

    def __init__(self,
                 mpc: MPController,
                 resource_configurer: ResourceConfigurer,
                 workloads: List[Workload],
                 actual: Dict[str, numpy.ndarray],
                 zookeeper_client_endpoint: str,
                 zookeeper_barrier_path: str,
                 real_simulation: bool):

        super().__init__(resource_configurer=resource_configurer,
                         workloads=workloads,
                         actual=actual,
                         zookeeper_client_endpoint=zookeeper_client_endpoint,
                         zookeeper_barrier_path=zookeeper_barrier_path,
                         real_simulation=real_simulation)
        self.mpc = mpc

    def create_new_configuration_from_window(self, time_step: int, window_size: int) -> None:
        print(f"Creating configuration for window size of {window_size}")
        new_configuration = self.resource_configurer.calculate_resource_configurations(
            ConfigurationWindow(
                simulation_time_step=time_step,
                window_size=window_size,
                starting_prediction=0
            )
        )
        if self.real_simulation:
            if time_step != 0:
                self.delete_jobs()
            self.create_workloads_from_configuration(new_configuration)
        self.current_config = new_configuration
        print(new_configuration)

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
            duration: float = self.simulate_timestep(
                time_step) if self.real_simulation else self.fake_simulate_timestep(time_step)
            print(f"{duration} at timestep {time_step}")
            total_duration += duration

        if self.real_simulation:
            self.delete_jobs()
        print(
            f"Simulation took {total_duration} total seconds, with {num_checkpoints} Checkpoints")
        print(
            f"With checkpoints, the total duration would be {total_duration + GANG_SCHEDULING_CHECKPOINT_PENALTY * num_checkpoints}")
        return total_duration


def generate_onetime_simulation() -> None:
    actual: Dict[str, numpy.ndarray] = get_actual_dict(WORKLOADS)
    for job_name in actual:
        workload = actual[job_name][:, 0]
        actual[job_name] = [workload]
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        workloads=WORKLOADS, predictions=actual)
    dynamic_mpc: DynamicMPController = DynamicMPController(
        resource_configurer=resource_configurer, simulation_length=GANG_SCHEDULING_SIMULATION_LENGTH, window_size=GANG_SCHEDULING_SIMULATION_LENGTH)
    dynamic_mpc.calculate_time_horizon(time_step=0)
    get_duration_from_plan(resource_configurer, dynamic_mpc.dp_window_sizes)


def get_duration_from_plan(resource_configurer: ResourceConfigurer, mpc_plan: numpy.ndarray) -> None:
    cur_plan: int = 0
    checkpoints: int = -1
    duration: float = 0
    current_config: Dict[str, int] = {}
    while cur_plan < GANG_SCHEDULING_SIMULATION_LENGTH:
        checkpoints += 1
        current_window: ConfigurationWindow = ConfigurationWindow(
            simulation_time_step=0,
            window_size=mpc_plan[cur_plan],
            starting_prediction=cur_plan
        )
        current_config = resource_configurer.calculate_resource_configurations(
            current_window
        )
        print(current_config)
        print(mpc_plan[cur_plan])
        duration += resource_configurer.calculate_estimated_runtime(
            current_config,
            current_window)
        cur_plan += mpc_plan[cur_plan]
    print(duration)
    print(f"{duration + checkpoints * GANG_SCHEDULING_CHECKPOINT_PENALTY}")


def main() -> None:

    predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    actual: Dict[str, numpy.ndarray] = get_actual_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        workloads=WORKLOADS, predictions=predictions)

    static_simulator: StaticSimulator = StaticSimulator(
        resource_configurer=resource_configurer,
        workloads=WORKLOADS,
        actual=actual,
        zookeeper_client_endpoint=ZOOKEEPER_CLIENT_ENDPOINT,
        zookeeper_barrier_path=ZOOKEEPER_BARRIER_PATH,
        real_simulation=False)
    static_simulator.simulate()
    for i in range(1, GANG_SCHEDULING_WINDOW_SIZE):
        static_mpc: StaticMPController = StaticMPController(
            resource_configurer=resource_configurer,
            window_size=i,
            simulation_length=GANG_SCHEDULING_SIMULATION_LENGTH
        )
        mpc_simulator: MPCSimulator = MPCSimulator(
            mpc=static_mpc,
            resource_configurer=resource_configurer,
            workloads=WORKLOADS,
            actual=predictions,
            zookeeper_client_endpoint=ZOOKEEPER_CLIENT_ENDPOINT,
            zookeeper_barrier_path=ZOOKEEPER_BARRIER_PATH,
            real_simulation=False
        )
        print(f"Simulating simulation for static window of size {i}")
        mpc_simulator.simulate()

    dynamic_mpc: MPController = DynamicMPController(
        resource_configurer=resource_configurer,
        window_size=GANG_SCHEDULING_WINDOW_SIZE,
        simulation_length=GANG_SCHEDULING_SIMULATION_LENGTH
    )
    mpc_simulator = MPCSimulator(
        mpc=dynamic_mpc,
        resource_configurer=resource_configurer,
        workloads=WORKLOADS,
        actual=predictions,
        zookeeper_client_endpoint=ZOOKEEPER_CLIENT_ENDPOINT,
        zookeeper_barrier_path=ZOOKEEPER_BARRIER_PATH,
        real_simulation=False
    )

    mpc_simulator.simulate()


if __name__ == "__main__":
    # main()
    generate_onetime_simulation()
