from os import stat
import numpy

from abc import ABC, abstractmethod
from typing import Dict
from simulation.config.config import GANG_SCHEDULING_WINDOW_SIZE, GANG_SCHEDULING_SIMULATION_LENGTH, GANG_SCHEDULING_CHECKPOINT_PENALTY
from simulation.forecaster.lstm_forecaster import get_predictions_dict
from simulation.shared.workloads import Workload, WORKLOADS
from simulation.gang_scheduling.resource_configurer import ResourceConfigurer, ConfigurationWindow


class MPController(ABC):
    def __init__(self, resource_configurer: ResourceConfigurer):
        self.resource_configurer = resource_configurer
        self.dp_durations = numpy.zeros(
            (GANG_SCHEDULING_SIMULATION_LENGTH,
             GANG_SCHEDULING_WINDOW_SIZE), dtype="float64")
        self.dp_window_sizes = numpy.zeros(
            (GANG_SCHEDULING_SIMULATION_LENGTH,
             GANG_SCHEDULING_WINDOW_SIZE), dtype="int"
        )

    @abstractmethod
    def calculate_time_horizon(self, time_step: int, current_config: Dict[str, int]) -> int:
        pass


class StaticMPController(MPController):
    def __init__(self, resource_configurer: ResourceConfigurer, static_window_size: int):
        super().__init__(resource_configurer=resource_configurer)
        self.static_window_size = static_window_size

    def calculate_time_horizon(self, time_step: int, _: Dict[str, int]) -> int:
        return self.static_window_size if time_step % self.static_window_size == 0 else 0


class DynamicMPController(MPController):
    def __init__(self, resource_configurer: ResourceConfigurer):
        super().__init__(resource_configurer=resource_configurer)

    def calculate_duration(self, configuration_window: ConfigurationWindow) -> float:
        resource_configuration: Dict[str, int] = self.resource_configurer.calculate_resource_configurations(
            configuration_window=configuration_window)
        return self.resource_configurer.calculate_estimated_runtime(resource_configuration=resource_configuration,
                                                                    configuration_window=configuration_window)

    def calculate_time_horizon_from_start(self, time_step: int, start: int) -> None:
        """
        Calculate the optimal time horizon for the next reconfiguration and memoize it.

        Args:
            time_step (int): The timestep of the simulation the MPC is on
            start (int): The starting point in the timestep that we are calculating from.
        """
        window_size: int
        window_durations: Dict[int, float] = {}
        for window_size in range(1, GANG_SCHEDULING_WINDOW_SIZE - start + 1):
            configuration_window: ConfigurationWindow = ConfigurationWindow(
                simulation_time_step=time_step, window_size=window_size, starting_prediction=start)
            end: int = window_size + start
            additional_duration: float = self.dp_durations[time_step][end] + \
                GANG_SCHEDULING_CHECKPOINT_PENALTY if end < GANG_SCHEDULING_WINDOW_SIZE else 0
            duration: float = self.calculate_duration(
                configuration_window) + GANG_SCHEDULING_CHECKPOINT_PENALTY
            window_durations[window_size] = duration + additional_duration
        min_window: int = min(window_durations,
                              key=window_durations.get)  # type: ignore
        self.dp_durations[time_step][start] = window_durations[min_window]
        self.dp_window_sizes[time_step][start] = min_window

    def calculate_time_horizon_for_current_config(self, time_step: int, current_config: Dict[str, int]) -> None:
        min_duration = float("inf")
        for config_keep_length in range(1, GANG_SCHEDULING_WINDOW_SIZE + 1):
            config_duration = self.resource_configurer.calculate_estimated_runtime(
                resource_configuration=current_config,
                configuration_window=ConfigurationWindow(
                    simulation_time_step=time_step, window_size=config_keep_length)
            )
            additional_duration: float = self.dp_durations[time_step][config_keep_length] + \
                GANG_SCHEDULING_CHECKPOINT_PENALTY if config_keep_length < GANG_SCHEDULING_WINDOW_SIZE else 0
            min_duration = min(
                min_duration, config_duration + additional_duration)
        if min_duration < self.dp_durations[time_step][0]:
            self.dp_durations[time_step][0] = min_duration
            self.dp_window_sizes[time_step][0] = 0

    def calculate_time_horizon(self, time_step: int, current_config: Dict[str, int]) -> int:
        for start in reversed(range(GANG_SCHEDULING_WINDOW_SIZE)):
            self.calculate_time_horizon_from_start(
                time_step=time_step, start=start)
        if len(current_config) != 0:
            self.calculate_time_horizon_for_current_config(
                time_step, current_config)
        return self.dp_window_sizes[time_step][0]


def main():
    predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        workloads=WORKLOADS, predictions=predictions)
    mpc: MPController = DynamicMPController(
        resource_configurer=resource_configurer)
    current_config: Dict[str, int] = {}
    for i in range(50):
        time_horizon = mpc.calculate_time_horizon(
            i, current_config=current_config)
        if time_horizon != 0:
            current_config = resource_configurer.calculate_resource_configurations(
                configuration_window=ConfigurationWindow(
                    simulation_time_step=i,
                    window_size=time_horizon,
                    starting_prediction=0
                )
            )
            print(current_config)
        print(mpc.dp_window_sizes[i])


if __name__ == "__main__":
    main()
