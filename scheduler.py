import logging
import os

import sentry_sdk
from redis import Redis
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq_scheduler import Scheduler
from sentry_sdk.integrations.flask import FlaskIntegration

from tasks import scrape_tracked_channels

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
RQ_QUEUE_NAME = os.environ.get("RQ_QUEUE_NAME", "channel-scrape")
TRACKED_CHANNELS_CRON = "0 0 * * *"
TRACKED_CHANNELS_CRON_JOB_ID = "daily-tracked-channels-scrape"

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
    )


def ensure_daily_tracking_schedule(
    scheduler: Scheduler, redis_connection: Redis
) -> None:
    """Keep exactly one tracked-channel daily cron registration."""
    try:
        existing_job = Job.fetch(
            TRACKED_CHANNELS_CRON_JOB_ID, connection=redis_connection
        )
        scheduler.cancel(existing_job)
    except NoSuchJobError:
        pass
    except Exception as e:
        logger.warning(
            "Could not cancel existing cron job '%s': %s",
            TRACKED_CHANNELS_CRON_JOB_ID,
            str(e),
        )

    scheduler.cron(
        TRACKED_CHANNELS_CRON,
        func=scrape_tracked_channels,
        id=TRACKED_CHANNELS_CRON_JOB_ID,
        queue_name=RQ_QUEUE_NAME,
        use_local_timezone=False,
    )
    logger.info(
        "Registered cron job '%s' (%s).",
        TRACKED_CHANNELS_CRON_JOB_ID,
        TRACKED_CHANNELS_CRON,
    )


def main() -> None:
    redis_connection = Redis.from_url(REDIS_URL)
    scheduler = Scheduler(queue_name=RQ_QUEUE_NAME, connection=redis_connection)
    ensure_daily_tracking_schedule(scheduler, redis_connection)
    scheduler.run()


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    main()
