from typing import List

from simulation.shared.workloads import Workload
from simulation.gang_scheduling.resource_configurer import ResourceConfigurer
from simulation.gang_scheduling.mpc import MPController


class GangScheduler:
    def __init__(self, workloads: List[Workload], resource_configurer: ResourceConfigurer, mpc: MPController):
        self.workload = workloads
        self.resource_configurer = resource_configurer
        self.mpc = mpc

    def gang_schedule():
        self.resource_configurer
