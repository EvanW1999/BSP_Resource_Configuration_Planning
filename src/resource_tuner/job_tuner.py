
from kubernetes import client, config, watch
from typing import List
from ..shared.types import Json


DEFAULT_NAMESPACE: str = "default"
NUM_ITERATIONS: int = 2
JOB_NAME: str = "qj-1"
KUBE_BATCH_GROUP_NAME: str = "scheduling.k8s.io/group-name"
POD_GROUP_NAME: str = "qj-1"
ITERATION_ENV_NAME: str = "NUM_ITERATIONS"

config.load_kube_config()
api_instance: client.BatchV1Api = client.BatchV1Api()


def create_job_object(cpu_iteration: int, num_iterations: int):
    metadata: client.V1ObjectMeta = client.V1ObjectMeta(
        namespace=DEFAULT_NAMESPACE, name=JOB_NAME)

    resource_requests: Json = {"cpu": f"{200 + 100 * cpu_iteration}m"}
    resource_requirements = client.V1ResourceRequirements(
        requests=resource_requests, limits=resource_requests)

    env_vars: List[client.V1EnvVar] = [client.V1EnvVar(
        name=ITERATION_ENV_NAME, value=str(num_iterations))]
    container = client.V1Container(
        name="matmul", env=env_vars, image="evanw1999/matmul:public", image_pull_policy="Always")
    container.resources = resource_requirements
    spec = client.V1PodSpec(
        containers=[container], restart_policy="Never", scheduler_name="kube-batch")

    template = client.V1PodTemplateSpec()
    template.metadata = client.V1ObjectMeta(
        annotations={KUBE_BATCH_GROUP_NAME: POD_GROUP_NAME})
    template.spec = spec

    body = client.V1Job(api_version="batch/v1", kind="Job")
    body.metadata = metadata
    body.spec = client.V1JobSpec(
        completions=NUM_ITERATIONS, parallelism=NUM_ITERATIONS, template=template)
    return body


def kube_create_job(cpu_iteration: int):
    api_instance.create_namespaced_job(
        DEFAULT_NAMESPACE, create_job_object(cpu_iteration, 10))


def get_job_duration():
    w = watch.Watch()
    for event in w.stream(api_instance.list_namespaced_job,
                          namespace=DEFAULT_NAMESPACE,
                          label_selector=f"job-name={JOB_NAME}"):
        job = event["object"]
        if job.status.succeeded == NUM_ITERATIONS:
            duration = (job.status.completion_time -
                        job.status.start_time).total_seconds()
            api_instance.delete_namespaced_job(
                JOB_NAME, DEFAULT_NAMESPACE, propagation_policy="Background")
            return duration


def tune_resources():
    for iteration in range(1, 5):
        kube_create_job(iteration)
        duration = get_job_duration()
        print(f"Iteration {iteration} took {duration} seconds")


def get_available_resources():
    cust: client.CustomObjectsApi = client.CustomObjectsApi()
    response: Json = cust.list_cluster_custom_object(
        'metrics.k8s.io', 'v1beta1', 'nodes')
    print(response)


def main():
    tune_resources()
    # get_available_resources()


if __name__ == "__main__":
    main()
