from stable_baselines3.common.base_class import BaseAlgorithm
from simulation.gang_scheduling.reinforcement import SimulatorEnv
import numpy

from abc import ABC, abstractmethod
from typing import Dict
from simulation.config.config import GANG_SCHEDULING_WINDOW_SIZE, GANG_SCHEDULING_SIMULATION_LENGTH, GANG_SCHEDULING_CHECKPOINT_PENALTY, FORECASTER_WINDOW_SIZE
from simulation.forecaster.lstm_forecaster import get_predictions_dict
from simulation.shared.workloads import Workload, WORKLOADS
from simulation.gang_scheduling.resource_configurer import ResourceConfigurer, ConfigurationWindow


class MPController(ABC):
    def __init__(self, resource_configurer: ResourceConfigurer, simulation_length: int, window_size: int):
        self.resource_configurer = resource_configurer
        self.simulation_length = simulation_length
        self.window_size = window_size
        self.dp_durations = numpy.zeros(self.window_size, dtype="float64")
        self.dp_window_sizes = numpy.zeros(self.window_size, dtype="int")

    @abstractmethod
    def calculate_time_horizon(self, time_step: int, current_config: Dict[str, int]) -> int:
        pass


class StaticMPController(MPController):
    def __init__(self, resource_configurer: ResourceConfigurer, simulation_length: int, window_size: int):
        super().__init__(resource_configurer=resource_configurer,
                         simulation_length=simulation_length, window_size=window_size)

    def calculate_time_horizon(self, time_step: int, _: Dict[str, int]) -> int:
        return self.window_size if time_step % self.window_size == 0 else 0


class DynamicMPController(MPController):
    def __init__(self, resource_configurer: ResourceConfigurer, simulation_length: int, window_size: int):
        super().__init__(resource_configurer=resource_configurer,
                         simulation_length=simulation_length, window_size=window_size)
        self.length_punishment = 1.02

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
        for window_size in range(1, min(self.window_size - start, self.simulation_length - time_step, FORECASTER_WINDOW_SIZE - 5) + 1):
            configuration_window: ConfigurationWindow = ConfigurationWindow(
                simulation_time_step=time_step, window_size=window_size, starting_prediction=start)
            end: int = window_size + start
            additional_duration: float = self.dp_durations[end] + \
                GANG_SCHEDULING_CHECKPOINT_PENALTY if end < self.window_size else 0
            duration: float = self.calculate_duration(
                configuration_window) * pow(self.length_punishment, window_size)

            window_durations[window_size] = duration + additional_duration
        min_window: int = min(window_durations,
                              key=window_durations.get)  # type: ignore
        self.dp_durations[start] = window_durations[min_window]
        self.dp_window_sizes[start] = min_window

    def calculate_time_horizon_for_current_config(self, time_step: int, current_config: Dict[str, int]) -> None:
        min_duration = float("inf")
        for config_keep_length in range(1, min(self.window_size, self.simulation_length - time_step) + 1):
            config_duration = self.resource_configurer.calculate_estimated_runtime(
                resource_configuration=current_config,
                configuration_window=ConfigurationWindow(
                    simulation_time_step=time_step, window_size=config_keep_length)
            ) * pow(self.length_punishment, config_keep_length)
            additional_duration: float = self.dp_durations[config_keep_length] + \
                GANG_SCHEDULING_CHECKPOINT_PENALTY if config_keep_length < GANG_SCHEDULING_WINDOW_SIZE else 0
            min_duration = min(
                min_duration, config_duration + additional_duration)
        if min_duration < self.dp_durations[0]:
            self.dp_durations[0] = min_duration
            self.dp_window_sizes[0] = 0

    def calculate_time_horizon(self, time_step: int, current_config: Dict[str, int] = {}) -> int:
        self.dp_durations = numpy.zeros(self.window_size, dtype="float64")
        self.dp_window_sizes = numpy.zeros(self.window_size, dtype="int")

        for start in reversed(range(min(self.window_size, self.simulation_length - time_step))):
            self.calculate_time_horizon_from_start(
                time_step=time_step, start=start)
        if time_step != 0:
            self.dp_durations[0] += GANG_SCHEDULING_CHECKPOINT_PENALTY
        if len(current_config) != 0:
            self.calculate_time_horizon_for_current_config(
                time_step, current_config)
        return self.dp_window_sizes[0]


class ReinforcementMPController(MPController):
    def __init__(self, model: BaseAlgorithm, env: SimulatorEnv, resource_configurer: ResourceConfigurer, simulation_length: int, window_size: int):
        super().__init__(resource_configurer=resource_configurer,
                         simulation_length=simulation_length, window_size=window_size)
        self.model = model
        self.env = env

    def calculate_time_horizon(self, time_step: int, current_config: Dict[str, int]) -> int:
        self.env.current_config = current_config
        observation: numpy.ndarray = self.env.get_state_from_time_step(
            time_step)
        return self.model.predict(
            observation, deterministic=True
        )[0]


def main():
    predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        workloads=WORKLOADS, predictions=predictions)


if __name__ == "__main__":
    main()
