import time
from kubernetes import client, config, watch
from typing import List, Dict

from kubernetes.client.exceptions import ApiException
from simulation.shared.types import Json
from simulation.shared.env_vars import EnvVarName

DEFAULT_NAMESPACE: str = "default"
STRESS_NG_IMAGE: str = "evanw1999/stress-ng:public"

# config.load_incluster_config()
config.load_kube_config()
api_instance: client.BatchV1Api = client.BatchV1Api()


def create_stress_body(env_vars: Dict[str, str], cpu_shares: int):
    job_name: str = env_vars[EnvVarName.JOB_NAME.value]

    metadata: client.V1ObjectMeta = client.V1ObjectMeta(
        namespace=DEFAULT_NAMESPACE, name=job_name, labels={"name": job_name})

    resource_requests: Json = {"cpu": f"{cpu_shares}m"}
    resource_requirements = client.V1ResourceRequirements(
        requests=resource_requests, limits=resource_requests)

    job_env_vars: List[client.V1EnvVar] = [client.V1EnvVar(
        name=name, value=value) for name, value in env_vars.items()]
    container = client.V1Container(
        name=job_name, env=job_env_vars, image=STRESS_NG_IMAGE, image_pull_policy="Always")
    container.resources = resource_requirements
    spec = client.V1PodSpec(
        containers=[container], restart_policy="Never")

    template = client.V1PodTemplateSpec()
    template.spec = spec

    body = client.V1Job(api_version="batch/v1", kind="Job")
    body.metadata = metadata
    body.spec = client.V1JobSpec(template=template)
    return body


def kube_create_stress_job(env_vars: Dict[str, str], cpu_shares: int):
    try:
        api_instance.create_namespaced_job(
            DEFAULT_NAMESPACE, create_stress_body(env_vars, cpu_shares))
    except ApiException as e:
        time.sleep(20)
        # print(e)
        kube_create_stress_job(env_vars, cpu_shares)


def kube_update_stress_job(env_vars: Dict[str, str], cpu_shares: int):
    kube_delete_job(env_vars[EnvVarName.JOB_NAME.value])
    kube_create_stress_job(env_vars, cpu_shares)


def kube_delete_job(job_name: str):
    api_instance.delete_namespaced_job(
        job_name, DEFAULT_NAMESPACE, propagation_policy="Foreground")


def get_job_duration() -> int:
    w = watch.Watch()
    for event in w.stream(api_instance.list_namespaced_job,
                          namespace=DEFAULT_NAMESPACE,
                          label_selector=f"job-name=matrix"):
        job = event["object"]
        if job.status.succeeded:
            duration = (job.status.completion_time -
                        job.status.start_time).total_seconds()
            api_instance.delete_namespaced_job(
                "matrix", DEFAULT_NAMESPACE, propagation_policy="Background")
            return duration
    return -1


def get_available_resources():
    cust: client.CustomObjectsApi = client.CustomObjectsApi()
    response: Json = cust.list_cluster_custom_object(
        'metrics.k8s.io', 'v1beta1', 'nodes')
    print(response)
