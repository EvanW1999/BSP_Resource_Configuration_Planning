import csv
from typing import TextIO, List, Union
from pathlib import Path


class StatLogger():
    def __init__(self, file_name: str):
        path: str = str(Path(__file__).parent.absolute())
        self.csv_file: TextIO = open(path + file_name, "w+")
        self.csv_writer: csv.writer = csv.writer(self.csv_file)

    def write_header(self, headers: List[str]):
        self.csv_writer.writerow(headers)

    def log_statistics(self, statistics: List[Union[float, int]]):
        self.csv_writer.writerow(statistics)

    def close_file(self):
        self.csv_file.close()

    def __del__(self):
        if not self.csv_file.closed:
            self.csv_file.close()