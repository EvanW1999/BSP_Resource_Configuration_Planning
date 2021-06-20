import pandas
import numpy
from scipy import interpolate
from typing import Dict, List, NamedTuple

from simulation.shared.workloads import Workload, WORKLOADS
from simulation.forecaster.lstm_forecaster import get_predictions_dict
from simulation.config.config import GANG_SCHEDULING_SHARE_INCREMENT, GANG_SCHEDULING_STARTING_SHARES, GANG_SCHEDULING_TOTAL_SHARES, PROFILER_OUTPUT_PATH, SIMULATION_DIR


class RunResult(NamedTuple):
    workload: Workload
    runtime: float
    workload_size: int
    cpu_shares: int


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

    def get_slowest_job(self, resource_configuration: Dict[str, int], timestep: int, forecast_step: int) -> RunResult:
        results: List[RunResult] = []

        for workload in self.workloads:
            workload_model: interpolate.interp2d = self.workload_models[workload.task.task_name]
            workload_size: int = self.predictions[workload.task.task_name][timestep][forecast_step]
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

    def increment_configuration(self, resource_configuration: Dict[str, int], timestep: int, configuration_window: int) -> None:

        forecast_step: int
        slowest_jobs: List[RunResult] = []
        for forecast_step in range(configuration_window):
            slowest_jobs.append(self.get_slowest_job(
                resource_configuration, timestep, forecast_step))
        job_to_increment: str = self.find_largest_improvement(slowest_jobs)
        resource_configuration[job_to_increment] += GANG_SCHEDULING_SHARE_INCREMENT

    def calculate_resource_configurations(self, timestep: int, configuration_window: int) -> Dict[str, int]:
        resource_configuration: Dict[str, int] = {
            workload.task.task_name: GANG_SCHEDULING_STARTING_SHARES for workload in self.workloads}

        print(GANG_SCHEDULING_STARTING_SHARES * len(self.workloads))
        print(GANG_SCHEDULING_TOTAL_SHARES)
        for _ in range(GANG_SCHEDULING_STARTING_SHARES * len(self.workloads),
                       GANG_SCHEDULING_TOTAL_SHARES, GANG_SCHEDULING_SHARE_INCREMENT):
            self.increment_configuration(
                resource_configuration=resource_configuration, timestep=timestep, configuration_window=configuration_window)
        return resource_configuration


def main():
    a: Dict[str, int] = {"a": 1, "b": 2, "c": 3}
    predictions: Dict[str, numpy.ndarray] = get_predictions_dict(WORKLOADS)
    resource_configurer: ResourceConfigurer = ResourceConfigurer(
        WORKLOADS, predictions)
    print(resource_configurer.calculate_resource_configurations(0, 1))
    # print(min(a, key=a.get))
    # print(SIMULATION_DIR)
    # print(PROFILER_OUTPUT_PATH)


if __name__ == "__main__":
    main()
