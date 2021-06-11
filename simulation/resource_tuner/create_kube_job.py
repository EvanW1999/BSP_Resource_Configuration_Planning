from kubernetes import client, config, watch
from typing import List, Dict
from simulation.shared.types import Json

DEFAULT_NAMESPACE: str = "default"
NUM_COMPLETIONS: int = 2
KUBE_BATCH_GROUP_NAME: str = "scheduling.k8s.io/group-name"
POD_GROUP_NAME: str = "qj-1"
ITERATION_ENV_NAME: str = "NUM_ITERATIONS"
JOB_ENV_NAME: str = "JOB_NAME"

config.load_incluster_config()
api_instance: client.BatchV1Api = client.BatchV1Api()


def create_job_object(env_vars: Dict[str, str], cpu_shares: int):
    job_name: str = env_vars[JOB_ENV_NAME]

    metadata: client.V1ObjectMeta = client.V1ObjectMeta(
        namespace=DEFAULT_NAMESPACE, name=job_name, labels={"name": job_name})

    resource_requests: Json = {"cpu": f"{cpu_shares}m"}
    resource_requirements = client.V1ResourceRequirements(
        requests=resource_requests, limits=resource_requests)

    job_env_vars: List[client.V1EnvVar] = [client.V1EnvVar(
        name=name, value=value) for name, value in env_vars.items()]
    container = client.V1Container(
        name=job_name, env=job_env_vars, image=f"evanw1999/stress-ng:public", image_pull_policy="Always")
    container.resources = resource_requirements
    spec = client.V1PodSpec(
        containers=[container], restart_policy="Never", scheduler_name="kube-batch")

    template = client.V1PodTemplateSpec()
    template.metadata = client.V1ObjectMeta(
        annotations={KUBE_BATCH_GROUP_NAME: POD_GROUP_NAME})
    template.spec = spec

    body = client.V1Job(api_version="batch/v1", kind="Job")
    body.metadata = metadata
    body.spec = client.V1JobSpec(template=template)
    return body


def kube_create_job(env_vars: Dict[str, str], cpu_shares: int):
    api_instance.create_namespaced_job(
        DEFAULT_NAMESPACE, create_job_object(env_vars, cpu_shares))


def kube_update_job(env_vars: Dict[str, str], cpu_shares: int):
    kube_delete_job(env_vars[JOB_ENV_NAME])
    kube_create_job(env_vars, cpu_shares)


def kube_delete_job(job_name: str):
    api_instance.delete_namespaced_job(
        job_name, DEFAULT_NAMESPACE, propagation_policy="Background")


def kube_create_multiple_jobs(matmul_iters: int, eigen_iters: int, matmul_cpu: int, eigen_cpu: int):
    metadata: client.V1ObjectMeta = client.V1ObjectMeta(
        namespace=DEFAULT_NAMESPACE, name=JOB_NAME)

    matmul_requests: Json = {"cpu": f"{matmul_cpu}m"}
    matmul_requirements = client.V1ResourceRequirements(
        requests=matmul_requests, limits=matmul_requests)

    eigen_requests: Json = {"cpu": f"{eigen_cpu}m"}
    eigen_requirements = client.V1ResourceRequirements(
        requests=eigen_requests, limits=eigen_requests
    )

    matmul_env: List[client.V1EnvVar] = [client.V1EnvVar(
        name=ITERATION_ENV_NAME, value=str(matmul_iters))]
    matmul_container = client.V1Container(
        name="matmul", env=matmul_env, image="evanw1999/matmul:public", image_pull_policy="Always")
    matmul_container.resources = matmul_requirements

    eigen_env: List[client.V1EnvVar] = [client.V1EnvVar(
        name=ITERATION_ENV_NAME, value=str(eigen_iters))]
    eigen_container = client.V1Container(
        name="eigen", env=eigen_env, image="evanw1999/eigen:public", image_pull_policy="Always")
    eigen_container.resources = eigen_requirements
    spec = client.V1PodSpec(
        containers=[matmul_container, eigen_container], restart_policy="Never", scheduler_name="kube-batch")

    template = client.V1PodTemplateSpec()
    template.metadata = client.V1ObjectMeta(
        annotations={KUBE_BATCH_GROUP_NAME: POD_GROUP_NAME})
    template.spec = spec

    body = client.V1Job(api_version="batch/v1", kind="Job")
    body.metadata = metadata
    body.spec = client.V1JobSpec(template=template)
    api_instance.create_namespaced_job(
        DEFAULT_NAMESPACE, body)


def get_job_duration() -> int:
    w = watch.Watch()
    for event in w.stream(api_instance.list_namespaced_job,
                          namespace=DEFAULT_NAMESPACE,
                          label_selector=f"job-name=matrix"):
        job = event["object"]
        if job.status.succeeded == NUM_COMPLETIONS:
            duration = (job.status.completion_time -
                        job.status.start_time).total_seconds()
            api_instance.delete_namespaced_job(
                "matrix", DEFAULT_NAMESPACE, propagation_policy="Background")
            return duration


def get_available_resources():
    cust: client.CustomObjectsApi = client.CustomObjectsApi()
    response: Json = cust.list_cluster_custom_object(
        'metrics.k8s.io', 'v1beta1', 'nodes')
    print(response)
