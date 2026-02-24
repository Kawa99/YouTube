import os

import sentry_sdk
from redis import Redis
from rq import Connection, Worker
from sentry_sdk.integrations.flask import FlaskIntegration

LISTEN_QUEUES = [os.environ.get("RQ_QUEUE_NAME", "channel-scrape")]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
    )


def main():
    redis_connection = Redis.from_url(REDIS_URL)
    with Connection(redis_connection):
        worker = Worker(LISTEN_QUEUES)
        worker.work()


if __name__ == "__main__":
    main()
