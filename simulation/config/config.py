from configobj import ConfigObj, Section
from pathlib import Path


PATH: str = str(Path(__file__).parent.absolute())


CONFIG: ConfigObj = ConfigObj(f"{PATH}/config.ini")


# Zookeeper config variables
ZOOKEEPER_SECTION: Section = CONFIG["zookeeper"]
ZOOKEEPER_CLIENT_ENDPOINT: str = ZOOKEEPER_SECTION["client_endpoint"]
ZOOKEEPER_BARRIER_PATH: str = ZOOKEEPER_SECTION["barrier_path"]

# Resource tuner config variables
RESOURCE_TUNER_SECTION: Section = CONFIG["resource_tuner"]
TUNER_MIN_SHARES: int = RESOURCE_TUNER_SECTION.as_int("min_shares")
TUNER_MAX_SHARES: int = RESOURCE_TUNER_SECTION.as_int("max_shares")
TUNER_SHARE_INCREMENT: int = RESOURCE_TUNER_SECTION.as_int("share_increment")
TUNER_TRIES: int = RESOURCE_TUNER_SECTION.as_int("num_tries")
TUNER_OUTPUT_PATH: str = RESOURCE_TUNER_SECTION["output_path"]

# Simulation config variables
STRESS_NG_SECTION: Section = CONFIG["stress-ng"]
SIMULATION_MIN_WORKLOAD: int = STRESS_NG_SECTION.as_int("min_workload")
SIMULATION_MAX_WORKLOAD: int = STRESS_NG_SECTION.as_int("max_workload")
SIMULATION_WORKLOAD_INCREMENT: int = STRESS_NG_SECTION.as_int(
    "workload_increment")
SIMULATION_TERMINAL_WORKLOAD: int = STRESS_NG_SECTION.as_int(
    "terminal_workload")
