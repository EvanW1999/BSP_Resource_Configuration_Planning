#!/usr/local/bin/python3
"""
This script is a scheduler to scheduler kubernetes jobs
"""

import random
import json

from kubernetes import client, config, watch

config.load_kube_config()
v1 = client.CoreV1Api()

SCHEDULER_NAME = "evanScheduler"


def nodes_available():
    ready_nodes = []
    for node in v1.list_node().items:
        for status in node.status.conditions:
            if status.status == "True" and status.type == "Ready":
                ready_nodes.append(node.metadata.name)
    return ready_nodes


def scheduler(name, node, namespace="default"):

    target = client.V1ObjectReference()
    target.kind = "Node"
    target.apiVersion = "v1"
    target.name = node

    meta = client.V1ObjectMeta()
    meta.name = name

    body = client.V1Binding(target=target)
    body.metadata = meta

    return v1.create_namespaced_binding(namespace, body)


def main():
    watcher = watch.Watch()
    for event in watcher.stream(v1.list_namespaced_pod, "default"):
        if event['object'].status.phase == "Pending" \
                and event['object'].spec.scheduler_name == SCHEDULER_NAME:
            try:
                scheduler(event['object'].metadata.name,
                          random.choice(nodes_available()))
            except client.rest.ApiException as e:
                print(json.loads(e.body)['message'])


if __name__ == '__main__':
    main()
