import pandas
import seaborn
import matplotlib.pyplot as plt
from typing import List

from simulation.config.config import SIMULATION_DIR, PROFILER_OUTPUT_PATH
from simulation.shared.workloads import Workload, WORKLOADS


def generate_workload_figures(workloads: List[Workload]):
    print(SIMULATION_DIR + PROFILER_OUTPUT_PATH)
    df: pandas.DataFrame = pandas.read_csv(
        SIMULATION_DIR + PROFILER_OUTPUT_PATH)
    plt.subplots(figsize=(10, 10))
    for workload in workloads:
        workload_df = df[df[df.columns[0]] ==
                         workload.task.task_name][df.columns[1:]]
        workload_df = workload_df.pivot(
            index=workload_df.columns[0], columns=workload_df.columns[1], values=workload_df.columns[2])
        # print(workload_df)
        # Sample figsize in inches
        seaborn.heatmap(workload_df)
        plt.savefig(
            f"{SIMULATION_DIR}/workload_profiler/figures/{workload.task.task_name}.png")
        plt.clf()


def main():
    generate_workload_figures(WORKLOADS)
