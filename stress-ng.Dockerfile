FROM python:3.8.5
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install stress-ng
RUN pip install pipenv
COPY ./Pipfile ./Pipfile.lock /user/home/
WORKDIR /user/home/
COPY ./simulation/shared/env_vars.py ./simulation/shared/
COPY ./simulation/__init__.py ./simulation/
COPY ./simulation/jobs/stress_ng.py ./simulation/jobs/
RUN pipenv install --system --deploy
ENV PYTHONPATH="$PYTHONPATH:/user/home"
CMD ["python", "simulation/jobs/stress_ng.py"]