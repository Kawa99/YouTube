import os

from redis import Redis
from rq import Connection, Worker

LISTEN_QUEUES = [os.environ.get("RQ_QUEUE_NAME", "channel-scrape")]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def main():
    redis_connection = Redis.from_url(REDIS_URL)
    with Connection(redis_connection):
        worker = Worker(LISTEN_QUEUES)
        worker.work()


if __name__ == "__main__":
    main()
