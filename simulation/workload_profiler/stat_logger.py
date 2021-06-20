import csv
from typing import TextIO, List, Union


class StatLogger():
    def __init__(self, file_path: str):
        self.csv_file: TextIO = open(file_path, "w+")
        self.csv_writer = csv.writer(self.csv_file)

    def write_header(self, headers: List[str]):
        self.csv_writer.writerow(headers)

    def log_statistics(self, statistics: List[Union[float, int, str]]):
        self.csv_writer.writerow(statistics)

    def close_file(self):
        self.csv_file.close()

    def __del__(self):
        if not self.csv_file.closed:
            self.csv_file.close()
