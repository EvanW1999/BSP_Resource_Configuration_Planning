from dataclasses import dataclass
from typing import List, Dict
from simulation.shared.env_vars import EnvVarName
from simulation.config.config import ZOOKEEPER_BARRIER_PATH, ZOOKEEPER_CLIENT_ENDPOINT


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
             task=Task(task_name="affinity", workload_param="--affinity-ops", workload_modifier=250000)),
    Workload(time_series=Series(file_name="nyc_taxi_2.csv"),
             task=Task(task_name="atomic", workload_param="--atomic-ops", workload_modifier=250000)),
    Workload(time_series=Series(file_name="nyc_taxi_3.csv"),
             task=Task(task_name="bsearch", workload_param="--bsearch-ops", workload_modifier=7500)),
    Workload(time_series=Series(file_name="exchange-2_cpm_results.csv"),
             task=Task(task_name="cache", workload_param="--cache-ops", workload_modifier=75)),
    Workload(time_series=Series(file_name="elb_request_count_8c0756_1.csv"),
             task=Task(task_name="chmod", workload_param="--chmod-ops", workload_modifier=4000)),
    Workload(time_series=Series(file_name="elb_request_count_8c0756_2.csv"),
             task=Task(task_name="matrix", workload_param="--matrix-ops", workload_modifier=50000)),
    Workload(time_series=Series(file_name="art_daily_small_noise.csv"),
             task=Task(task_name="memcpy", workload_param="--memcpy-ops", workload_modifier=5000)),
    Workload(time_series=Series(file_name="ambient_temperature_system_failure_1.csv"),
             task=Task(task_name="poll", workload_param="--poll-ops", workload_modifier=500000)),
    Workload(time_series=Series(file_name="ambient_temperature_system_failure_2.csv"),
             task=Task(task_name="vecmath", workload_param="--vecmath-ops", workload_modifier=20000)),
    Workload(time_series=Series(file_name="exchange-2_cpc_results.csv"),
             task=Task(task_name="zero", workload_param="--zero-ops", workload_modifier=200000))
]


def get_env_vars(task: Task, num_tasks: int = len(WORKLOADS)) -> Dict[str, str]:
    return {
        EnvVarName.NUM_TASKS.value: str(num_tasks),
        EnvVarName.JOB_NAME.value: task.task_name,
        EnvVarName.OP_NAME.value: task.workload_param,
        EnvVarName.WORKLOAD_MODIFIER.value: str(task.workload_modifier),
        EnvVarName.PYTHONUNBUFFERED.value: "1",
        EnvVarName.NUM_INSTANCES.value: "0",
        EnvVarName.ZOOKEEPER_CLIENT_ENDPOINT.value: ZOOKEEPER_CLIENT_ENDPOINT,
        EnvVarName.BARRIER_PATH.value: ZOOKEEPER_BARRIER_PATH
    }
