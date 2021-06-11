import numpy
import pandas
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from pathlib import Path
from typing import List, Tuple


def get_traffic_data(traffic_file: str) -> numpy.ndarray:
    traffic_df: pandas.DataFrame = pandas.read_csv(
        traffic_file, usecols=["traffic_volume"])
    traffic_values: numpy.ndarray = traffic_df.values.astype('float32')
    return traffic_values


# convert an array of values into a dataset matrix
def create_dataset(dataset, look_back=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return numpy.array(dataX), numpy.array(dataY)


def scale_traffic_data(traffic_values: numpy.ndarray) -> numpy.ndarray:
    scaler: MinMaxScaler = MinMaxScaler(feature_range=(5, 20))
    return scaler.fit_transform(traffic_values)


def get_lstm_model() -> Sequential:
    model: Sequential = Sequential()
    model.add(LSTM(4, input_shape=(1, 1)))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    return model


def get_resource_train_data(num_partitions: int, traffic_file: str) -> List[numpy.ndarray]:
    traffic_values: numpy.ndarray = get_traffic_data(traffic_file)
    traffic_values = scale_traffic_data(traffic_values)

    return numpy.split(traffic_values, num_partitions)


def make_prediction(data: numpy.ndarray) -> Tuple[numpy.ndarray, numpy.ndarray]:
    train_x: numpy.ndarray
    test_x: numpy.ndarray
    look_back: int = 1

    [train_data, test_data] = numpy.split(data, 2)
    train_x, train_y = create_dataset(train_data, look_back)
    test_x, test_y = create_dataset(test_data, look_back)
    train_x = numpy.reshape(train_x, (train_x.shape[0], 1, train_x.shape[1]))
    test_x = numpy.reshape(test_x, (test_x.shape[0], 1, test_x.shape[1]))

    model: Sequential = get_lstm_model()
    model.fit(train_x, train_y, epochs=10, batch_size=10, verbose=2)
    test_predict: numpy.ndarray = model.predict(test_x)
    return test_predict[:, 0], test_y


def forecast_resource_usage():
    path: str = str(Path(__file__).parent.absolute())
    traffic_file: str = path + "/data/Metro_Interstate_Traffic_Volume.csv"
    results_file: str = path + "/data/forecast_results.csv"

    eigen_data: numpy.ndarray
    matmul_data: numpy.ndarray
    [eigen_data, matmul_data] = get_resource_train_data(2, traffic_file)
    predicted_eigen, actual_eigen = make_prediction(eigen_data)
    predicted_matmul, actual_matmul = make_prediction(matmul_data)

    forecast_results: numpy.ndarray = numpy.column_stack((predicted_eigen, actual_eigen,
                                                          predicted_matmul, actual_matmul))
    numpy.savetxt(results_file, forecast_results, delimiter=",", fmt='%f')


def main():
    numpy.random.seed(1)
    forecast_resource_usage()


if __name__ == "__main__":
    main()
