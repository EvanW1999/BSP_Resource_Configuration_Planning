from kubernetes import client, config, watch


DEFAULT_NAMESPACE = "default"
NUM_ITERATIONS = 2
JOB_NAME = "qj-1"

config.load_kube_config()
api_instance = client.BatchV1Api()


def create_job_object():
    metadata = client.V1ObjectMeta(
        namespace=DEFAULT_NAMESPACE, name=JOB_NAME)

    resource_requests = {"cpu": "500m"}
    resource_requirements = client.V1ResourceRequirements(
        requests=resource_requests, limits=resource_requests)
    container = client.V1Container(
        name="matmul", image="evanw1999/matmul:public")
    container.resources = resource_requirements
    spec = client.V1PodSpec(
        containers=[container], restart_policy="Never", scheduler_name="kube-batch")

    template = client.V1PodTemplateSpec()
    template.metadata = client.V1ObjectMeta()
    template.spec = spec

    body = client.V1Job(api_version="batch/v1", kind="Job")
    body.metadata = metadata
    body.spec = client.V1JobSpec(
        completions=NUM_ITERATIONS, parallelism=NUM_ITERATIONS, template=template)
    return body


def kube_create_job():
    api_instance.create_namespaced_job(DEFAULT_NAMESPACE, create_job_object())


def process_jobs():
    w = watch.Watch()
    for event in w.stream(api_instance.list_namespaced_job,
                          namespace=DEFAULT_NAMESPACE,
                          label_selector=f"job-name={JOB_NAME}"):
        job = event["object"]
        if job.status.succeeded == NUM_ITERATIONS:
            duration = (job.status.completion_time -
                        job.status.start_time).total_seconds()
            print(f"Job took {duration} seconds")
            api_instance.delete_namespaced_job(
                JOB_NAME, DEFAULT_NAMESPACE, propagation_policy="Background")
            return


def main():
    # kube_create_job()
    process_jobs()


if __name__ == "__main__":
    main()
