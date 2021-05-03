import numpy
import pandas
import math
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from pathlib import Path

numpy.random.seed(1)

path: str = str(Path(__file__).parent.absolute())
traffic_df: pandas.DataFrame = pandas.read_csv(
    path + "/data/Metro_Interstate_Traffic_Volume.csv", usecols=["traffic_volume"])
traffic_values: numpy.ndarray = traffic_df.values.astype('float32')

scaler: MinMaxScaler = MinMaxScaler(feature_range=(5, 20))
traffic_values = scaler.fit_transform(traffic_values)

print(traffic_values)


train_size: int = int(len(traffic_values) * 0.5)
train_data: numpy.ndarray = traffic_values[0:train_size, :]


# convert an array of values into a dataset matrix
def create_dataset(dataset, look_back=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return numpy.array(dataX), numpy.array(dataY)


look_back: int = 1

train_x: numpy.ndarray
train_y: numpy.ndarray
train_x, train_y = create_dataset(traffic_values, look_back)

# reshape input to be [samples, time steps, features]
train_x = numpy.reshape(train_x, (train_x.shape[0], 1, train_x.shape[1]))


model: Sequential = Sequential()
model.add(LSTM(4, input_shape=(1, look_back)))
model.add(Dense(1))
model.compile(loss='mean_squared_error', optimizer='adam')
model.fit(train_x, train_y, epochs=10, batch_size=10, verbose=2)


model_prediction = model.predict(train_x)
print(model_prediction)
print(train_y)
train_score: float = math.sqrt(
    mean_squared_error(train_y, model_prediction[:, 0]))
print(train_score)
