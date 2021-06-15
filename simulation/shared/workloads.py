from dataclasses import dataclass
from typing import List


Series: dataclass = dataclass


@dataclass(frozen=True)
class Series:
    file_name: str
    target_col: str = "value"
    n_rows: int = 1500
    n_test: int = 500


@dataclass(frozen=True)
class Task:
    task_name: str
    workload_param: str
    workload_modifier: int = 1000


@dataclass(frozen=True)
class Workload:
    time_series: Series
    task: Task


WORKLOADS: List[Workload] = [
    Workload(time_series=Series(file_name="nyc_taxi_1.csv"),
             task=Task(task_name="aoil", workload_param="--aiol-ops")),
    Workload(time_series=Series(file_name="nyc_taxi_2.csv"),
             task=Task(task_name="atomic", workload_param="--atomic-ops")),
    Workload(time_series=Series(file_name="nyc_taxi_3.csv"),
             task=Task(task_name="branch", workload_param="--branch-ops")),
    Workload(time_series=Series(file_name="exchange-2_cpm_results.csv"),
             task=Task(task_name="bsearch", workload_param="--bsearch-ops")),
    Workload(time_series=Series(file_name="elb_request_count_8c0756_1.csv"),
             task=Task(task_name="cache", workload_param="--cache-ops")),
    Workload(time_series=Series(file_name="elb_request_count_8c0756_2.csv"),
             task=Task(task_name="matrix", workload_param="--matrix-ops")),
    Workload(time_series=Series(file_name="art_daily_small_noise.csv"),
             task=Task(task_name="memcpy", workload_param="--memcpy-ops")),
    Workload(time_series=Series(file_name="ambient_temperature_system_failure_1.csv"),
             task=Task(task_name="mq", workload_param="--mq-ops")),
    Workload(time_series=Series(file_name="ambient_temperature_system_failure_2.csv"),
             task=Task(task_name="vecmath", workload_param="--vecmath-ops"))
]
