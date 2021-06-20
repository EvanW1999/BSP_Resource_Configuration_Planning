import numpy
import pandas

from pathlib import Path
from sklearn.linear_model import LinearRegression
from statistics import mean
from typing import Tuple, List
from simulation.shared.types import Json
from simulation.shared.create_kube_job import kube_create_multiple_jobs, get_job_duration


PATH: str = str(Path(__file__).parent.absolute())
ROWS_PER_JOB: int = 24
NUM_RESULTS: int = 10


def get_profiling_data() -> Tuple[pandas.DataFrame, pandas.DataFrame]:
    profiling_file: str = PATH + "/forecaster/data/resource_profiling.csv"
    profiling_df: pandas.DataFrame = pandas.read_csv(profiling_file)
    return profiling_df.head(ROWS_PER_JOB), profiling_df.tail(ROWS_PER_JOB)


def get_simulator_model(df: pandas.DataFrame) -> LinearRegression:
    data_x: numpy.ndarray = df[df.columns[0:2]].values.astype("float32")
    data_y: numpy.ndarray = df[df.columns[2]].values.astype("float32")
    return LinearRegression().fit(data_x, data_y)


def train_simulator_models() -> Tuple[LinearRegression, LinearRegression]:
    matmul_df: pandas.DataFrame
    eigen_df: pandas.DataFrame
    matmul_df, eigen_df = get_profiling_data()

    matmul_model: LinearRegression = get_simulator_model(matmul_df)
    eigen_model: LinearRegression = get_simulator_model(eigen_df)
    return matmul_model, eigen_model


def calculate_config(matmul_model: LinearRegression, eigen_model: LinearRegression, matmul_iters: int = 12,  eigen_iters: int = 12) -> Tuple[float, float]:
    matmul_cpu: int = 200
    eigen_cpu: int = 200

    for i in range(14):
        matmul_duration_est: float = matmul_model.predict(
            numpy.array([[matmul_iters, matmul_cpu]]))[0]
        eigen_duration_est: float = eigen_model.predict(
            [[eigen_iters, eigen_cpu]])[0]
        if matmul_duration_est > eigen_duration_est:
            matmul_cpu += 100
        else:
            eigen_cpu += 100
    return matmul_cpu, eigen_cpu


def simulate_exppo(matmul_model: LinearRegression, eigen_model: LinearRegression, forecast_df: pandas.DataFrame):
    matmul_cpu: int
    eigen_cpu: int
    matmul_cpu, eigen_cpu = calculate_config(matmul_model, eigen_model)
    matmul_iters: numpy.ndarray = forecast_df["actual_matmul"].values.astype(
        "float32")
    eigen_iters: numpy.ndarray = forecast_df["actual_eigen"].values.astype(
        "float32")
    durations: List[float] = []
    for iteration in range(NUM_RESULTS):
        kube_create_multiple_jobs(
            int(matmul_iters[iteration]), int(eigen_iters[iteration]), matmul_cpu, eigen_cpu)
        duration: int = get_job_duration()
        durations.append(duration)
        print(duration)
    print(mean(durations))


def simulate_predictive(matmul_model: LinearRegression, eigen_model: LinearRegression, forecast_df: pandas.DataFrame):
    matmul_cpu: int
    eigen_cpu: int
    matmul_iters: numpy.ndarray = forecast_df["actual_matmul"].values.astype(
        "float32")
    eigen_iters: numpy.ndarray = forecast_df["actual_eigen"].values.astype(
        "float32")
    predicted_eigen: numpy.ndarray = forecast_df["predicted_eigen"].values.astype(
        "float32")
    predicted_matmul: numpy.ndarray = forecast_df["predicted_matmul"].values.astype(
        "float32")

    durations: List[float] = []
    for iteration in range(NUM_RESULTS):
        matmul_cpu, eigen_cpu = calculate_config(
            matmul_model, eigen_model, predicted_matmul[iteration], predicted_eigen[iteration])
        kube_create_multiple_jobs(
            int(matmul_iters[iteration]), int(eigen_iters[iteration]), matmul_cpu, eigen_cpu)
        duration: float = get_job_duration()
        durations.append(duration)
        print(duration)
    print(mean(durations))


def simulate():
    forecast_file: str = PATH + "/forecaster/data/forecast_results.csv"
    forecast_df: pandas.DataFrame = pandas.read_csv(
        forecast_file, nrows=NUM_RESULTS)
    matmul_model: LinearRegression
    eigen_model: LinearRegression
    matmul_model, eigen_model = train_simulator_models()
    simulate_exppo(matmul_model, eigen_model, forecast_df)
    simulate_predictive(matmul_model, eigen_model, forecast_df)


def main() -> None:
    simulate()


if __name__ == "__main__":
    main()
