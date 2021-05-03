from kubernetes import client, config, watch
from typing import List
from .create_kube_job import kube_create_job, get_job_duration
from .stat_logger import StatLogger
from ..shared.types import Json

CSV_HEADER: List[str] = ["num_iterations", "cpu_shares", "duration"]


class ResourceTuner():
    def __init__(self):
        self.stat_logger: StatLogger = StatLogger(
            "/../forecaster/data/resource_profiling.csv")
        self.stat_logger.write_header(CSV_HEADER)

    def profile_cpu_configuration(self, num_iterations: int, image: str) -> None:
        cpu_shares: int
        for cpu_shares in range(200, 2000, 300):
            kube_create_job(num_iterations, cpu_shares, image)
            duration: float = get_job_duration()
            print(
                f"{num_iterations} Iterations, {cpu_shares} CPU Shares, {duration} Seconds")
            self.stat_logger.log_statistics(
                [num_iterations, cpu_shares, duration])

    def profile_resource_configurations(self, images: List[str]) -> None:
        num_iterations: int
        image: str
        for image in images:
            for num_iterations in range(5, 25, 5):
                self.profile_cpu_configuration(num_iterations, image)
        self.stat_logger.close_file()


def main():
    # tune_resources()
    resource_tuner: ResourceTuner = ResourceTuner()
    resource_tuner.profile_resource_configurations(["matmul", "eigen"])
    # get_available_resources()


if __name__ == "__main__":
    main()
