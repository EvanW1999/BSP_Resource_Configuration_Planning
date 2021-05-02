FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y python3-pip
RUN pip3 install numpy

COPY jobs/eigen.py /home/jobs/
CMD python3 /home/jobs/eigen.py