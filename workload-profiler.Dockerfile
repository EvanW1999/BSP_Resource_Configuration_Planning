FROM python:3.8.5
RUN apt-get -y update
RUN apt-get -y upgrade
RUN pip install --upgrade pip
RUN pip install pipenv 
WORKDIR /user/home/
COPY ./Pipfile ./Pipfile.lock ./
COPY ./simulation ./simulation
RUN pipenv install --system --deploy
ENV PYTHONPATH="$PYTHONPATH:/user/home"
CMD ["python", "simulation/workload_profiler/workload_profiler.py"]