import simulation
import pandas
import numpy
from scipy import interpolate
from dataclasses import dataclass
from typing import Dict, List

from simulation.shared.workloads import Workload, WORKLOADS
from simulation.forecaster.lstm_forecaster import get_predictions_dict
from simulation.config.config import (GANG_SCHEDULING_SHARE_INCREMENT, GANG_SCHEDULING_STARTING_SHARES,
                                      GANG_SCHEDULING_TOTAL_SHARES, PROFILER_OUTPUT_PATH, SIMULATION_DIR)


@dataclass(frozen=True)
class RunResult:
    workload: Workload
    runtime: float
    workload_size: int
    cpu_shares: int


@dataclass(frozen=True)
class ConfigurationWindow:
    simulation_time_step: int
    window_size: int
    starting_prediction: int = 0


class ResourceConfigurer:
    def __init__(self, workloads: List[Workload], predictions: Dict[str, numpy.ndarray]) -> None:
        self.profiling_df: pandas.DataFrame = pandas.read_csv(
            SIMULATION_DIR + PROFILER_OUTPUT_PATH, dtype={0: str, 1: "float64", 2: "float64", 3: "float64"})
        self.workloads: List[Workload] = workloads
        self.workload_models: Dict[str,
                                   interpolate.interp2d] = self.create_workload_models()
        self.predictions: Dict[str, numpy.ndarray] = predictions

    def create_workload_models(self) -> Dict[str, interpolate.interp2d]:
        workload_models: Dict[str, interpolate.interp2d] = {}
        workload: Workload
        for workload in self.workloads:
            workload_values: numpy.ndarray = self.profiling_df[
                self.profiling_df[self.profiling_df.columns[0]] == workload.task.task_name].values
            workload_models[workload.task.task_name] = interpolate.interp2d(
                workload_values[:, 1].astype("float64"),
                workload_values[:, 2].astype("float64"),
                workload_values[:, 3].astype("float64"))
        return workload_models

    def get_slowest_job(self, resource_configuration: Dict[str, int], configuration_window: ConfigurationWindow, forecast_step: int) -> RunResult:
        results: List[RunResult] = []

        for workload in self.workloads:
            workload_model: interpolate.interp2d = self.workload_models[workload.task.task_name]
            workload_size: int = self.predictions[workload.task.task_name][
                configuration_window.simulation_time_step][configuration_window.starting_prediction + forecast_step]
            cpu_shares: int = resource_configuration[workload.task.task_name]

            duration: float = workload_model(workload_size, cpu_shares)
            results.append(RunResult(workload=workload, runtime=duration,
                           workload_size=workload_size, cpu_shares=cpu_shares))
        return max(results, key=lambda result: result.runtime)

    def find_largest_improvement(self, slowest_jobs: List[RunResult]) -> str:
        improvements: Dict[str, float] = {
            job.workload.task.task_name: 0 for job in slowest_jobs}

        for job in slowest_jobs:
            workload_model: interpolate.interp2d = self.workload_models[job.workload.task.task_name]
            new_runtime: int = workload_model(
                job.workload_size, job.cpu_shares + GANG_SCHEDULING_SHARE_INCREMENT)
            improvements[job.workload.task.task_name] += job.runtime - new_runtime
        return min(improvements, key=improvements.get)  # type: ignore

    def increment_configuration(self, resource_configuration: Dict[str, int], configuration_window: ConfigurationWindow) -> None:

        forecast_step: int
        slowest_jobs: List[RunResult] = []
        for forecast_step in range(configuration_window.window_size):
            slowest_jobs.append(self.get_slowest_job(
                resource_configuration, configuration_window, forecast_step))
        job_to_increment: str = self.find_largest_improvement(slowest_jobs)
        resource_configuration[job_to_increment] += GANG_SCHEDULING_SHARE_INCREMENT

    def calculate_resource_configurations(self, configuration_window: ConfigurationWindow) -> Dict[str, int]:
        resource_configuration: Dict[str, int] = {
            workload.task.task_name: GANG_SCHEDULING_STARTING_SHARES for workload in self.workloads}

        for _ in range(GANG_SCHEDULING_STARTING_SHARES * len(self.workloads),
                       GANG_SCHEDULING_TOTAL_SHARES, GANG_SCHEDULING_SHARE_INCREMENT):
            self.increment_configuration(
                resource_configuration=resource_configuration, configuration_window=configuration_window)
        return resource_configuration

    def calculate_estimated_runtime(self, resource_configuration: Dict[str, int], configuration_window: ConfigurationWindow) -> float:
        total_runtime: float = 0
        forecast_step: int
        for forecast_step in range(configuration_window.window_size):
            total_runtime += self.get_slowest_job(resource_configuration=resource_configuration,
                                                  configuration_window=configuration_window, forecast_step=forecast_step).runtime
        return total_runtime


def main():
    predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        WORKLOADS, predictions)
    print(resource_configurer.calculate_resource_configurations(ConfigurationWindow(
        simulation_time_step=0, window_size=10, starting_prediction=0)))


if __name__ == "__main__":
    main()
