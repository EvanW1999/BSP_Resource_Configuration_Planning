# Kube_Gang_Scheduling

The goal of this repository is to test resource configuration planning algorithms on Bulk Synchronous Parallel jobs.

We use [stress-ng](https://wiki.ubuntu.com/Kernel/Reference/stress-ng) benchmarks as example workloads in our BSP jobs.
ZooKeeper is used to synchronize the supersteps of the Bulk Synchronous Parallel jobs, in order to ensure that all jobs wait until the slowest job has finished it's superset.

This repository allows us to run a BSP job on a Kubernetes cluster (where we actually run each task and record the duration) as well as to run workload simulations over simulated data (where we use predicted runtimes for each task).
For running over simulated data, we only need to do the following:

- If we want to generate new time-series workload-data, run the [lstm_forecaster](#time-series-forecasting)
- If we want to generate new output data, run the [workload profiler](#workload-profiling) on a Kubernetes cluster
- Run [simulations](#running-simulation) with `real_simulation=False`

### **Requirements**

- [pipenv](https://github.com/pypa/pipenv) (Install with `sudo apt-get install pipenv`)
- python >= 3.8.5
- Kubernetes Cluster (only required for profiling and non-simulation testing)

### **Setup**

1. Clone the repository.
2. Install dependencies with `pipenv install -d`.
3. Activate the environment with `pipenv shell`.

## **Workload Profiling**

In order to run simulations on simulated jobs, we want to produce data-points for how each of the component jobs (stress-ng benchmarks) perform
under different combinations of workloads and resource allocations.

This step is only necessary if you want to generate a new set of output data rather than re-use what's already computed in `workload_profiling.csv`.

This profiler is going to iterate through each of the configured workloads in `simulation/shared/workloads.py`. Each of the workloads consists of the following:

- The stress-ng benchmark that corresponds with the workload
- The workload parameter that is used to modify the amount of work that the benchmark is required to do
- A base-line modifier for how large that workload parameter is set to

The workload profiler should be run as a Kubernetes Job, which will be doing the following:

- For each combination of workload and CPU resources, we create a Kubernetes job with those specs
  - We specify CPU cores by attaching [resource requests/limits](https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource/) to the job.
- It will pass in workloads to the stress-NG benchmark via ZooKeeper and time the runtime multiple times

The configurations defined in `simulation/config/config.ini` (min, max, and intervals) decide which combinations of workload sizes and CPU cores are used by the workload profiler.
It will output a CSV with the following columns:

- Task Name, Workload Size, CPU Shares, and Average Duration

### **Running the Workload Profiler**

- Make sure that zookeeper is running in your Kubernetes cluster (you can create a deployment with `kubectl create -f deployments/zookeeper.yaml`).
- You can create the workload profiling job by using `kubectl create -f deployments/workload-profiler.yaml`.
- If any changes were made to the code/configuration variables, you will need to create a new workload profiler Docker image.
  Use the `workload-profiler.Dockerfile` to generate a new image, and edit `deployments/workload-profiler.yaml` to use the new image instead of `evanw1999/workload-profiler:public`.
- The profiling results can be gotten from the logs of the jobs.

## **Time Series Forecasting**

The time-series data is used to model time-series fluctations in the workloads of our jobs. The forecasts are what are fed as inputs into our models.

- The [Numenta time series datasets](https://www.numenta.com/resources/htm/numenta-anomoly-benchmark/) are found in `simulation/forecaster/data` directory.
- The forecasts are found in the `simulation/forecaster/forecasts` directory.
- In order to recompute forecasted values based on the "actual workloads", run the `lstm_forecaster.py` script (does not need to be run on Kubernetes).

## **Resource Configurer**

This component implements the `Resource Configuration Algorithm` defined in the thesis. At a high-level, it takes in:

- Predictions for workload sizes for each job
- Profiling data for how long each job took with different workload sizes and resource allocations
- How many steps we want to define a resource configuration for

In order to come up with a resource allocation, it starts each job at the minimum resource allocation, and does the following:

1. Given the current resource allocation and predicted workloads, interpolate over profiling data to predict the runtime for each job at each timestep
2. Calculate the slowest job at each timestep
3. For each of the slowest jobs, estimate the total improvement from adding resources to that job across all timesteps
4. Continuously add resources to the job that gives the overall highest improvement until there are no more resources remaining
5. Output resulting simulation environment

## **Running Simulation**

For running simulations, we can plug in multiple different controller algorithms for calculating the window size.

- The `StaticMPController` always returns a pre-determined window size based on `window_size`
- The `DynamicMPController` implements the `Dynamic MPC` algorithm described in the thesis
- The `ReinforcementMPController` implements the reinforcement learning algorithm for calculating window sizes

If we want to run a simulation with simulated data, we simply need to set `real_simulation=False` in `simulation/simulator.py` and run the script (does not need to necessarily be run in a Kubernetes cluster).

If we want to run a simulation with real jobs on a Kubernetes cluster, we need to do the following:

- Set `real_simulation = True`
- Make sure that zookeeper is running in your Kubernetes cluster (you can create a deployment with `kubectl create -f deployments/zookeeper.yaml`).
- Use the `simulator.Dockerfile` to create a Docker Container
- Run the job via `kubctl create -f deployments/simulator.yaml`

We have both the actual time-series data and the predictions made by our LSTM model to use to model changes in task workloads.
The predictions are used in our configuration algorithm which decides how our resources are distributed across tasks.
For the task workloads actually used in the simulation, we can use either the actual time-series data or the LSTM predictions (if we want to run a simulation assuming we have perfect knowledge of future workloads).

The overall simulation duration consists of the sum of the durations at each time-step of the BSP job and `# of checkpoints * checkpoint_penalty` (configured in `config.ini`).

### **Reinforcement Learning**

In order to train our reinfrocement learning model, we use the OpenAI Gym library.
In our environment, we define our reward function to reduce both the duration of the BSP timesteps as well as the number of reconfigurations (which is equivalent to reducing the duration calculated in the simulation).
In order to train the model, run `python simulation/gang_scheduling/reinforcement.py`.
The trained model will be saved in `simulation/gang_scheduling/models`.