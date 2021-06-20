import numpy

from abc import ABC, abstractmethod
from typing import List, Dict
from simulation.shared.workloads import Workload
from simulation.gang_scheduling.resource_configurer import ResourceConfigurer


class MPController(ABC):
    def __init__(self, workloads: List[Workload], resource_configurer: ResourceConfigurer, predictions: Dict[str, numpy.ndarray]):
        self.workloads = workloads
        self.resource_configurer = resource_configurer
        self.predictions = predictions

    @abstractmethod
    def calculate_time_horizon(self, predictions: numpy.ndarray) -> int:
        pass


class DynamicMPController(MPController):
    def __init__(self, workloads: List[Workload], resource_configurer: ResourceConfigurer, predictions: Dict[str, numpy.ndarray]):
        super().__init__(workloads=workloads, resource_configurer=resource_configurer, predictions=predictions)

    def calculate_time_horizon(self, predictions: numpy.ndarray) -> int:
        return super().calculate_time_horizon(predictions)
