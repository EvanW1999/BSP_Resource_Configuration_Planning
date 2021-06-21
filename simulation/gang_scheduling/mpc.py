import numpy

from abc import ABC, abstractmethod
from typing import List, Dict
from simulation.config.config import GANG_SCHEDULING_WINDOW_SIZE, GANG_SCHEDULING_SIMULATION_LENGTH, GANG_SCHEDULING_CHECKPOINT_PENALTY
from simulation.forecaster.lstm_forecaster import get_predictions_dict
from simulation.shared.workloads import Workload, WORKLOADS
from simulation.gang_scheduling.resource_configurer import ResourceConfigurer, ConfigurationWindow


class MPController(ABC):
    def __init__(self, resource_configurer: ResourceConfigurer, predictions: Dict[str, numpy.ndarray]):
        self.resource_configurer = resource_configurer
        self.predictions = predictions
        self.dp_durations = numpy.zeros(
            (GANG_SCHEDULING_SIMULATION_LENGTH,
             GANG_SCHEDULING_WINDOW_SIZE), dtype="float64")
        self.dp_window_sizes = numpy.zeros(
            (GANG_SCHEDULING_SIMULATION_LENGTH,
             GANG_SCHEDULING_WINDOW_SIZE), dtype="int"
        )

    @abstractmethod
    def calculate_time_horizon(self, time_step: int) -> int:
        pass


class DynamicMPController(MPController):
    def __init__(self, resource_configurer: ResourceConfigurer, predictions: Dict[str, numpy.ndarray]):
        super().__init__(resource_configurer=resource_configurer, predictions=predictions)

    def calculate_duration(self, configuration_window: ConfigurationWindow) -> float:
        resource_configuration: Dict[str, int] = self.resource_configurer.calculate_resource_configurations(
            configuration_window=configuration_window)
        return self.resource_configurer.calculate_estimated_runtime(resource_configuration=resource_configuration,
                                                                    configuration_window=configuration_window)

    def calculate_time_horizon_from_start(self, time_step: int, start: int) -> None:
        window_size: int
        window_durations: Dict[int, float] = {}
        for window_size in range(1, GANG_SCHEDULING_WINDOW_SIZE - start + 1):
            configuration_window: ConfigurationWindow = ConfigurationWindow(
                simulation_time_step=time_step, window_size=window_size, starting_prediction=start)
            end: int = window_size + start
            additional_duration: float = self.dp_durations[time_step][end] + \
                GANG_SCHEDULING_CHECKPOINT_PENALTY if end < GANG_SCHEDULING_WINDOW_SIZE else 0
            window_durations[window_size] = self.calculate_duration(
                configuration_window) + additional_duration
        min_window = min(window_durations,
                         key=window_durations.get)  # type: ignore
        self.dp_durations[time_step][start] = window_durations[min_window]
        self.dp_window_sizes[time_step][start] = min_window

    def calculate_time_horizon(self, time_step: int) -> int:
        for start in reversed(range(GANG_SCHEDULING_WINDOW_SIZE)):
            self.calculate_time_horizon_from_start(
                time_step=time_step, start=start)
        return self.dp_window_sizes[time_step][0]


def main():
    predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        workloads=WORKLOADS, predictions=predictions)
    mpc: MPController = DynamicMPController(
        resource_configurer=resource_configurer, predictions=predictions)
    print(mpc.calculate_time_horizon(0))


if __name__ == "__main__":
    main()
