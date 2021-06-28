import pandas
import numpy
import statistics
from operator import attrgetter
from scipy import interpolate
from dataclasses import dataclass
from typing import Dict, List

from simulation.shared.workloads import Workload, WORKLOADS
from simulation.forecaster.lstm_forecaster import get_predictions_dict, get_actual_dict
from simulation.config.config import (GANG_SCHEDULING_MAX_SHARES, GANG_SCHEDULING_SHARE_INCREMENT, GANG_SCHEDULING_STARTING_SHARES,
                                      GANG_SCHEDULING_TOTAL_SHARES, PROFILER_MAX_SHARES, PROFILER_MIN_SHARES, PROFILER_OUTPUT_PATH, PROFILER_SHARE_INCREMENT, SIMULATION_DIR, SIMULATION_MAX_WORKLOAD, SIMULATION_MIN_WORKLOAD, SIMULATION_WORKLOAD_INCREMENT)


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
        self.profiling_df: pandas.Dataframe = pandas.read_csv(
            SIMULATION_DIR + PROFILER_OUTPUT_PATH, dtype={0: str, 1: "float64", 2: "float64", 3: "float64"})
        self.workloads: List[Workload] = workloads
        self.workload_models: Dict[str,
                                   interpolate.RectBivariateSpline] = self.create_workload_models()
        self.predictions: Dict[str, numpy.ndarray] = predictions
        self.delta = 0.95

    def create_workload_models(self) -> Dict[str, interpolate.RectBivariateSpline]:
        workload_models: Dict[str, interpolate.RectBivariateSpline] = {}
        workload: Workload
        cpu_shares: numpy.ndarray = numpy.arange(
            PROFILER_MIN_SHARES, PROFILER_MAX_SHARES, PROFILER_SHARE_INCREMENT)
        workloads: numpy.ndarray = numpy.arange(
            SIMULATION_MIN_WORKLOAD, SIMULATION_MAX_WORKLOAD, SIMULATION_WORKLOAD_INCREMENT
        )
        for workload in self.workloads:
            workload_values: numpy.ndarray = self.profiling_df[self.profiling_df[self.profiling_df.columns[0]] ==
                                                               workload.task.task_name].sort_values(by=[self.profiling_df.columns[1],
                                                                                                        self.profiling_df.columns[2]]).values
            durations: numpy.ndarray = numpy.reshape(
                workload_values[:, 3], (len(workloads), len(cpu_shares)))

            workload_models[workload.task.task_name] = interpolate.RectBivariateSpline(
                workloads,
                cpu_shares,
                durations)
        return workload_models

    def get_slowest_job(self, resource_configuration: Dict[str, int], configuration_window: ConfigurationWindow, forecast_step: int) -> RunResult:
        results: List[RunResult] = []

        for workload in self.workloads:
            workload_model: interpolate.RectBivariateSpline = self.workload_models[
                workload.task.task_name]
            workload_size: int = self.predictions[workload.task.task_name][
                configuration_window.simulation_time_step][configuration_window.starting_prediction + forecast_step]
            cpu_shares: int = resource_configuration[workload.task.task_name]

            duration: float = workload_model(
                workload_size, cpu_shares, grid="False")[0][0]
            results.append(RunResult(workload=workload, runtime=duration,
                           workload_size=workload_size, cpu_shares=cpu_shares))
            # print(f"{duration}, {workload.task.task_name}, {workload_size}")
        return max(results, key=lambda result: result.runtime)

    def find_largest_improvement(self, slowest_jobs: List[RunResult]) -> str:
        improvements: Dict[str, float] = {}

        for count, job in enumerate(slowest_jobs):
            workload_model: interpolate.RectBivariateSpline = self.workload_models[
                job.workload.task.task_name]
            new_runtime: int = workload_model(
                job.workload_size, job.cpu_shares + GANG_SCHEDULING_SHARE_INCREMENT)
            # if job.runtime < new_runtime:
            # print(f"{job} has decreased runtime with increased CPU Shares")
            improvement: float = pow(self.delta, count) * \
                (job.runtime - new_runtime)
            if job.workload.task.task_name not in improvements:
                improvements[job.workload.task.task_name] = improvement
            else:
                improvements[job.workload.task.task_name] += improvement

        # for job_name, improvement in improvements.items():
        #     print(f"{job_name}, improvement= {improvement}")

        return max(improvements, key=improvements.get)  # type: ignore

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

    def increment_static_configuration(self, resource_configuration: Dict[str, int]) -> None:
        workload: Workload
        workload_size: int = int(statistics.mean(
            [SIMULATION_MIN_WORKLOAD, SIMULATION_MAX_WORKLOAD]))
        job_runtimes: List[RunResult] = []
        for workload in self.workloads:
            workload_model: interpolate.RectBivariateSpline = self.workload_models[
                workload.task.task_name]
            cpu_shares: int = resource_configuration[workload.task.task_name]
            if cpu_shares < GANG_SCHEDULING_MAX_SHARES:
                job_runtimes.append(RunResult(
                    workload=workload, runtime=workload_model(
                        workload_size, cpu_shares),
                    workload_size=workload_size, cpu_shares=cpu_shares))
        slowest_result: RunResult = max(
            job_runtimes, key=attrgetter("runtime"))
        resource_configuration[slowest_result.workload.task.task_name] += GANG_SCHEDULING_SHARE_INCREMENT

    def calculate_static_configuration(self) -> Dict[str, int]:
        resource_configuration: Dict[str, int] = {
            workload.task.task_name: GANG_SCHEDULING_STARTING_SHARES for workload in self.workloads}
        for _ in range(GANG_SCHEDULING_STARTING_SHARES * len(self.workloads),
                       GANG_SCHEDULING_TOTAL_SHARES, GANG_SCHEDULING_SHARE_INCREMENT):
            self.increment_static_configuration(
                resource_configuration=resource_configuration)
        return resource_configuration

    def calculate_estimated_runtime(self, resource_configuration: Dict[str, int], configuration_window: ConfigurationWindow) -> float:
        total_runtime: float = 0
        forecast_step: int
        for forecast_step in range(configuration_window.window_size):
            slowest_job: RunResult = self.get_slowest_job(resource_configuration=resource_configuration,
                                                          configuration_window=configuration_window, forecast_step=forecast_step)
            # print(slowest_job)
            total_runtime += slowest_job.runtime
        return total_runtime


def main():
    # predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    actual: Dict[str, numpy.ndarray] = get_actual_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        WORKLOADS, actual)
    print(resource_configurer.workload_models["atomic"](
        30, 3500, grid="False"))
    print(resource_configurer.workload_models["atomic"](
        30, 3600, grid="False"))
    print(resource_configurer.workload_models["atomic"](
        32, 3700, grid="False"))
    print(resource_configurer.workload_models["atomic"](
        33, 3500, grid="False"))

    # print(resource_configurer.calculate_static_configuration())
    # for i in range(10):
    #     configuration_window: ConfigurationWindow = ConfigurationWindow(
    #         simulation_time_step=0, window_size=i + 1, starting_prediction=0)
    #     resource_configuration: Dict[str, int] = resource_configurer.calculate_resource_configurations(
    #         configuration_window)
    #     # print(resource_configuration)
    #     # for time_step in range(4, 6):
    #     #     for workload in WORKLOADS:
    #     #         job_name: str = workload.task.task_name
    #     #         print(
    #     #             f"{job_name}, {time_step},  {resource_configurer.workload_models[job_name](actual[job_name][time_step][0], resource_configuration[job_name])}, {actual[job_name][time_step][0]}")
    #     print(resource_configuration)
    #     print(resource_configurer.calculate_estimated_runtime(
    #         resource_configuration=resource_configuration, configuration_window=configuration_window) / (i + 1))


if __name__ == "__main__":
    main()
