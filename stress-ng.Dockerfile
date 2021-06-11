FROM python:3.8.5
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install stress-ng
RUN pip install pipenv
COPY ./Pipfile ./Pipfile.lock /user/home/
WORKDIR /user/home/
COPY ./jobs/stress_ng.py jobs/
RUN pipenv install --system --deploy
CMD ["python", "jobs/stress_ng.py"]