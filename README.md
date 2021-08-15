# BSP_Resource_Configuration_Planning
The goal of this repository is to test resource configuration planning algorithms on Bulk Synchronous Parallel jobs. <br>
We use [stress-ng](https://wiki.ubuntu.com/Kernel/Reference/stress-ng) benchmarks as the tasks of the BSP job, and enforce synchronization using zookeeper.
Each task is given a unique time-series dataset in order to simulate fluctuations in its workload.

Using workload profiling, we can estimate the runtime of each task under different workloads.
Resource configuration planning algorithms are used to determine the amount of CPU shares given to each task at each time step.
These algorithms can be run in a simulated environment (where we use predicted runtimes for each task) or on a real Kubernetes environment (where we actually run each task and record the duration).

### **Requirements**
- [pipenv](https://github.com/pypa/pipenv) (Install with `sudo apt-get install pipenv`)
- python >= 3.8.5
- Kubernetes Cluster (only required for profiling and non-simulation testing)

### **Setup**
1. Clone the repository.
2. Install dependencies with `pipenv install`.
3. Activate the environment with `pipenv shell`.
4. Modify parameters in `simulation/config/config.ini` as needed.

### **Workload Profiling**
First make sure that zookeeper is running in your Kubernetes cluster (you can create a deployment with `kubectl create -f deployments/zookeeper.yaml`).

If any changes were made to the code/configuration variables, you will need to create a new workload profiler Docker image.
Use the `workload-profiler.Dockerfile` to generate a new image.
Edit `deployments/workload-profiler.yaml` to use the new image instead of `evanw1999/workload-profiler:public`. <br>
Create the workload profiling job using `kubectl create -f deployments/workload-profiler.yaml`.
You can get the profiling results from the logs of the job.



Alternatively, you may skip all of this and reuse the precomputed profiling data in `simulation/workload_profiler/results/workload_profiling.csv`.

### **Time Series Forecasting**
The time series datasets are found in `simulation/forecaster/data` directory.
The forecasts are found in the `simulation/forecaster/forecasts` directory.

In order to recompute forecasted values based on the "actual workloads", run the `lstm_forecaster.py` script.

### **Running Simulation**

### **Reinforcement Learning**
