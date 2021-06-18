from kazoo.client import KazooClient
from kazoo.recipe.queue import LockingQueue
from typing import List

UTF_ENCODING: str = "utf-16"


JOB_NAMES: List[str] = ["matrix", "vecmath"]


def main() -> None:
    zk: KazooClient = KazooClient(hosts='10.1.69.17:2181')
    zk.start()

    job_name: str
    locking_queues: List[LockingQueue] = list(
        map(lambda name: LockingQueue(zk, f"/{name}"), JOB_NAMES))

    for locking_queue in locking_queues:
        locking_queue.put(bytes([25]))


if __name__ == "__main__":
    main()
