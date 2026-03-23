"""Background tasks package — TaskIQ broker, workers and scheduled jobs."""

from typing import Any

from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.config import settings

_redis_url = str(settings.REDIS_URL)

result_backend: RedisAsyncResultBackend[Any] = RedisAsyncResultBackend(_redis_url)
broker = ListQueueBroker(url=_redis_url).with_result_backend(result_backend)

import app.tasks.certificate_tasks  # noqa: E402, F401
import app.tasks.email_tasks  # noqa: E402, F401
import app.tasks.payment_webhook_tasks  # noqa: E402, F401
import app.tasks.profile_tasks  # noqa: E402, F401
import app.tasks.scheduler  # noqa: E402, F401
import app.tasks.telegram_tasks  # noqa: E402, F401
