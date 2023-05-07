import numpy
import pandas
from keras.models import Sequential
from keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from pathlib import Path
from typing import List, Tuple, Dict
from math import sqrt
import matplotlib.pyplot as plt


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))


from simulation.config.config import SIMULATION_MIN_WORKLOAD, SIMULATION_MAX_WORKLOAD, FORECASTER_WINDOW_SIZE
from simulation.shared.workloads import WORKLOADS, Workload, Series


PATH: str = str(Path(__file__).parent.absolute())
HEADER: str = "t, t+1, t+2, t+3, t+4, t+5, t+6, t+7, t+8, t+9, t+10, t+11, t+12, t+13, t+14, t+15, t+16, t+17, t+18, t+19"


STANDARD_SCALER: MinMaxScaler = MinMaxScaler(
    feature_range=(SIMULATION_MIN_WORKLOAD, SIMULATION_MAX_WORKLOAD))


def plot_series_data() -> None:
    for workload in WORKLOADS:
        series_path: str = f"{PATH}/data/{workload.time_series.file_name}"
        series_df: pandas.DataFrame = pandas.read_csv(
            series_path, usecols=[workload.time_series.target_col], nrows=1500, dtype="float32")
        series_df = series_df.iloc[::5]
        series_df.reset_index().plot(
            x="index", y=workload.time_series.target_col, figsize=(10, 5))
        plt.savefig(
            f"{PATH}/figures/{workload.time_series.file_name[:-4]}.png")


def get_series_data(series_data: Series) -> pandas.DataFrame:
    series_path: str = f"{PATH}/data/{series_data.file_name}"
    series_df: pandas.DataFrame = pandas.read_csv(
        series_path, usecols=[series_data.target_col], nrows=5000, dtype="float32")
    return series_df


def series_to_supervised(series: numpy.ndarray, n_in: int, n_out: int) -> pandas.DataFrame:
    """Convert a time series dataset into a supervised learning dataset

    Args:
        series (numpy.ndarray): The series dataset
        n_in (int): The number of input variables (amount of timesteps to look backwards)
        n_out (int): THe number of output variables (amount of timsteps to predict forwards)

    Returns:
        pandas.DataFrame: The supervised learning dataset
    """

    df: pandas.DataFrame = pandas.DataFrame(series)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('t-%d' % (i))]
    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        names += [('t' if i == 0 else 't+%d' % (i))]
        # put it all together

    agg: pandas.DataFrame = pandas.concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    agg.dropna(inplace=True)
    return agg


def create_differenced_series(dataset: numpy.ndarray, interval: int = 1) -> numpy.ndarray:
    """Create a series of the differences between the value of time T and the value at time T - interval

    Args:
        dataset (numpy.ndarray): The dataset to calculate the differenced series on.
        interval (int, optional): Interval for how many timesteps to look backwards on. Defaults to 1.

    Returns:
        numpy.ndarray: The differenced series
    """
    diff = list()
    for i in range(interval, len(dataset)):
        value = dataset[i] - dataset[i - interval]
        diff.append(value)
    return numpy.array(diff)


def prepare_data(data: pandas.DataFrame, n_test: int, n_lag: int, n_seq: int) -> Tuple[MinMaxScaler, numpy.ndarray, numpy.ndarray]:
    """Prepare the data by scaling and creating a supervised dataset

    Args:
        data (pandas.DataFrame): The time-series data
        n_test (int): The number of samples to use for testing
        n_lag (int): The number of timesteps to look backwards when making predictions
        n_seq (int): The number of timesteps to look forwards for each prediction

    Returns:
        Tuple[MinMaxScaler, numpy.ndarray, numpy.ndarray]: The Scaler, the supervised training dataset, the supervised test dataset
    """
    values: numpy.ndarray = data.to_numpy()

    diff_values: numpy.ndarray = create_differenced_series(values)
    scaler: MinMaxScaler = MinMaxScaler(feature_range=(-1, 1))
    scaled_diff: numpy.ndarray = scaler.fit_transform(diff_values)

    supervised: pandas.DataFrame = series_to_supervised(
        scaled_diff, n_lag, n_seq)
    supervised_values: numpy.ndarray = supervised.to_numpy()

    train: numpy.ndarray
    test: numpy.ndarray
    train, test = supervised_values[0: -n_test], supervised_values[-n_test:]
    return scaler, train, test


def fit_lstm(train: numpy.ndarray, n_lag: int, n_batch: int, nb_epoch: int, n_neurons: int) -> Sequential:
    """Fit LSTM neural network to training data

    Args:
        train (numpy.ndarray): The training dataset
        n_lag (int): Number of timesteps to look backwards when making predictions
        n_batch (int): Batch size for model fitting
        nb_epoch (int): Number of epochs for training
        n_neurons (int): Number of neurons for the neural networ

    Returns:
        Sequential: The trained LSTM Neural Network
    """
    # reshape training into [samples, timesteps, features]
    X, y = train[:, 0:n_lag], train[:, n_lag:]
    X = X.reshape(X.shape[0], 1, X.shape[1])
    # design network
    model: Sequential = Sequential()
    model.add(LSTM(n_neurons, batch_input_shape=(
        n_batch, X.shape[1], X.shape[2]), stateful=True))
    model.add(Dense(y.shape[1]))
    model.compile(loss='mean_squared_error', optimizer='adam')
    # fit network
    for _ in range(nb_epoch):
        model.fit(X, y, epochs=1, batch_size=n_batch, verbose=0, shuffle=False)
        model.reset_states()
    return model

# make one forecast with an LSTM,


def forecast_lstm(model: Sequential, X: numpy.ndarray, n_batch: int) -> List[float]:
    # reshape input pattern to [samples, timesteps, features]
    X = X.reshape(1, 1, len(X))
    # make forecast
    forecast = model.predict(X, batch_size=n_batch)
    # convert to array
    return [x for x in forecast[0, :]]


def make_forecasts(model: Sequential, n_batch: int, test: numpy.ndarray, n_lag: int) -> numpy.ndarray:
    forecasts: List[List[float]] = list()
    for i in range(len(test)):
        X = test[i, 0:n_lag]
        # make forecast
        forecast = forecast_lstm(model, X, n_batch)
        # store the forecast
        forecasts.append(forecast)
    return numpy.array(forecasts)


# invert differenced forecast
def inverse_difference(last_ob: int, forecast: List[float]) -> List[float]:
    # invert first forecast
    inverted = list()
    inverted.append(forecast[0] + last_ob)
    # propagate difference forecast using inverted first value
    for i in range(1, len(forecast)):
        inverted.append(forecast[i] + inverted[i-1])
    return inverted

# inverse data transform on forecasts


def inverse_transform(series: pandas.DataFrame, forecasts: numpy.ndarray, scaler, n_test) -> numpy.ndarray:
    inverted: List[List[float]] = list()
    for i in range(len(forecasts)):
        # create array from forecast
        forecast: numpy.ndarray = numpy.array(forecasts[i])
        forecast = forecast.reshape(1, len(forecast))
        # invert scaling
        inv_scale: numpy.ndarray = scaler.inverse_transform(forecast)
        inv_scale = inv_scale[0, :]
        # invert differencing
        index: int = len(series) - n_test + i - 1
        last_ob: int = series.values[index]
        inv_diff = inverse_difference(last_ob, inv_scale)
        # store
        inverted.append(inv_diff)
    return numpy.array(inverted)

# evaluate the RMSE for each forecast time step


def evaluate_forecasts(test: numpy.ndarray, forecasts: numpy.ndarray, n_seq: int) -> None:
    scaled_actual = STANDARD_SCALER.fit_transform(test)
    scaled_predicted = STANDARD_SCALER.fit_transform(forecasts)
    for i in range(n_seq):
        scaled_actual_col = [row[i] for row in scaled_actual]
        scaled_predicted_col = [row[i] for row in scaled_predicted]
        rmse_scaled = sqrt(mean_squared_error(
            scaled_actual_col, scaled_predicted_col))
        print('t+%d Scaled RMSE: %f' % ((i+1), rmse_scaled))


def save_results(file_name: str, actual: numpy.ndarray, forecasts: numpy.ndarray) -> None:
    actual_file: str = f"{PATH}/actual/{file_name[:-4]}_actual.csv"
    forecasts_file: str = f"{PATH}/forecasts/{file_name[:-4]}_forecasts.csv"

    numpy.savetxt(actual_file, actual,
                  delimiter=",", fmt="%f", header=HEADER)
    numpy.savetxt(forecasts_file, forecasts,
                  delimiter=",", fmt="%f", header=HEADER)


def forecast_workload(series_data: Series) -> None:
    print(f"Forecasts for {series_data.file_name}")
    series_df: pandas.DataFrame = get_series_data(series_data)

    n_lag: int = 1
    n_seq: int = FORECASTER_WINDOW_SIZE
    n_test: int = series_data.n_test

    scaler: MinMaxScaler
    train: numpy.ndarray
    test: numpy.ndarray
    scaler, train, test = prepare_data(series_df, n_test, n_lag, n_seq)

    sequential: Sequential = fit_lstm(train, n_lag, 1, 100, 4)
    forecasts: numpy.ndarray = make_forecasts(sequential, 1, test, n_lag)
    forecasts = inverse_transform(
        series_df, forecasts, scaler, n_test + n_seq - 1)

    actual: numpy.ndarray = numpy.array([row[n_lag:] for row in test])
    actual = inverse_transform(
        series_df, actual, scaler, n_test + n_seq - 1)

    actual = numpy.reshape(actual, (n_test, n_seq))
    forecasts = numpy.reshape(forecasts, (n_test, n_seq))

    evaluate_forecasts(actual, forecasts, n_seq)
    save_results(series_data.file_name, actual, forecasts)


def forecast_workloads() -> None:
    workload: Workload
    for workload in WORKLOADS:
        forecast_workload(workload.time_series)


def get_predictions_dict(workloads: List[Workload]) -> Dict[str, numpy.ndarray]:
    predictions: Dict[str, numpy.ndarray] = {}
    for workload in workloads:
        forecasts_file = f"{PATH}/forecasts/{workload.time_series.file_name[:-4]}_forecasts.csv"
        workload_predictions: numpy.ndarray = pandas.read_csv(
            forecasts_file, dtype="float64").values
        predictions[workload.task.task_name] = STANDARD_SCALER.fit_transform(
            workload_predictions)
    return predictions


def get_actual_dict(workloads: List[Workload]) -> Dict[str, numpy.ndarray]:
    actual: Dict[str, numpy.ndarray] = {}
    for workload in workloads:
        actual_file = f"{PATH}/actual/{workload.time_series.file_name[:-4]}_actual.csv"
        workload_actual: numpy.ndarray = pandas.read_csv(
            actual_file, dtype="float64").values
        actual[workload.task.task_name] = STANDARD_SCALER.fit_transform(
            workload_actual
        )
    return actual


def main():
    # plot_series_data()
    forecast_workloads()


if __name__ == "__main__":
    main()
