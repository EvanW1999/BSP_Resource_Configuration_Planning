FROM python:3.8
RUN pip install pipenv
COPY ./Pipfile ./Pipfile.lock /user/home/
WORKDIR /user/home/
COPY ./jobs/stress_matmul.py jobs/
RUN pipenv install --system --deploy
CMD ["python", "jobs/stress_matmul.py"]


