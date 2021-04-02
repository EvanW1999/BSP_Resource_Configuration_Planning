from kubernetes import client, config, watch


DEFAULT_NAMESPACE = "default"
NUM_ITERATIONS = 2
JOB_NAME = "qj-1"

config.load_kube_config()
api_instance = client.BatchV1Api()


def create_job_object(iteration):
    metadata = client.V1ObjectMeta(
        namespace=DEFAULT_NAMESPACE, name=JOB_NAME)

    resource_requests = {"cpu": f"{200 + 100 * iteration}m"}
    resource_requirements = client.V1ResourceRequirements(
        requests=resource_requests, limits=resource_requests)
    container = client.V1Container(
        name="matmul", image="evanw1999/matmul:public", image_pull_policy="Always")
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


def kube_create_job(iteration):
    api_instance.create_namespaced_job(
        DEFAULT_NAMESPACE, create_job_object(iteration))


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


def main():
    tune_resources()


if __name__ == "__main__":
    main()
