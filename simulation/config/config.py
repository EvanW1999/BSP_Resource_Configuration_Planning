from configobj import ConfigObj, Section
from pathlib import Path


SIMULATION_DIR: str = str(Path(__file__).parent.parent.absolute())


CONFIG: ConfigObj = ConfigObj(f"{SIMULATION_DIR}/config/config.ini")


# Zookeeper config variables
ZOOKEEPER_SECTION: Section = CONFIG["zookeeper"]
ZOOKEEPER_CLIENT_ENDPOINT: str = ZOOKEEPER_SECTION["client_endpoint"]
ZOOKEEPER_BARRIER_PATH: str = ZOOKEEPER_SECTION["barrier_path"]

# Resource tuner config variables
WORKLOAD_PROFILER_SECTION: Section = CONFIG["workload_profiler"]
PROFILER_MIN_SHARES: int = WORKLOAD_PROFILER_SECTION.as_int("min_shares")
PROFILER_MAX_SHARES: int = WORKLOAD_PROFILER_SECTION.as_int("max_shares")
PROFILER_SHARE_INCREMENT: int = WORKLOAD_PROFILER_SECTION.as_int(
    "share_increment")
PROFILER_TRIES: int = WORKLOAD_PROFILER_SECTION.as_int("num_tries")
PROFILER_OUTPUT_PATH: str = WORKLOAD_PROFILER_SECTION["output_path"]

# Forecasting config variables
FORECASTER_SECTION: Section = CONFIG["forecaster"]
FORECASTER_WINDOW_SIZE: int = FORECASTER_SECTION.as_int("forecast_window")

# Simulation config variables
STRESS_NG_SECTION: Section = CONFIG["stress-ng"]
SIMULATION_MIN_WORKLOAD: int = STRESS_NG_SECTION.as_int("min_workload")
SIMULATION_MAX_WORKLOAD: int = STRESS_NG_SECTION.as_int("max_workload")
SIMULATION_WORKLOAD_INCREMENT: int = STRESS_NG_SECTION.as_int(
    "workload_increment")

# Gang scheduling config variables
GANG_SCHEDULING_SECTION: Section = CONFIG["gang-scheduling"]
GANG_SCHEDULING_STARTING_SHARES: int = GANG_SCHEDULING_SECTION.as_int(
    "starting_shares")
GANG_SCHEDULING_MAX_SHARES: int = GANG_SCHEDULING_SECTION.as_int("max_shares")
GANG_SCHEDULING_SHARE_INCREMENT: int = GANG_SCHEDULING_SECTION.as_int(
    "share_increment")
GANG_SCHEDULING_TOTAL_SHARES: int = GANG_SCHEDULING_SECTION.as_int(
    "total_shares")
GANG_SCHEDULING_WINDOW_SIZE: int = GANG_SCHEDULING_SECTION.as_int(
    "window_size")
GANG_SCHEDULING_CHECKPOINT_PENALTY: int = GANG_SCHEDULING_SECTION.as_int(
    "checkpoint_penalty"
)
GANG_SCHEDULING_SIMULATION_LENGTH: int = GANG_SCHEDULING_SECTION.as_int(
    "simulation_length"
)
