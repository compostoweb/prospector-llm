from __future__ import annotations

from fnmatch import fnmatch

from scheduler.beats import CELERY_BEAT_SCHEDULE
from workers.celery_app import (
    ALL_WORKER_QUEUES,
    CONTENT_WORKER_QUEUES,
    GENERAL_WORKER_QUEUES,
    celery_app,
)


def _route_queue_for_task(task_name: str) -> str:
    routes = celery_app.conf.task_routes or {}
    if isinstance(routes, dict):
        for pattern, route in routes.items():
            if fnmatch(task_name, pattern):
                return route["queue"]
    return celery_app.conf.task_default_queue


def test_worker_topology_uses_two_services_and_all_declared_queues() -> None:
    queue_names = {queue.name for queue in celery_app.conf.task_queues}

    assert GENERAL_WORKER_QUEUES == ("capture", "enrich", "cadence", "dispatch")
    assert CONTENT_WORKER_QUEUES == ("content", "content-engagement")
    assert queue_names == set(ALL_WORKER_QUEUES)


def test_all_included_worker_modules_route_to_managed_queue() -> None:
    managed_queues = set(ALL_WORKER_QUEUES)

    for module_name in celery_app.conf.include:
        queue_name = _route_queue_for_task(f"{module_name}.example_task")
        assert queue_name in managed_queues, module_name


def test_beat_tasks_route_to_general_or_content_worker() -> None:
    managed_queues = set(ALL_WORKER_QUEUES)

    for schedule_name, schedule in CELERY_BEAT_SCHEDULE.items():
        task_name = schedule["task"]
        options = schedule.get("options") or {}
        queue_name = options.get("queue") or _route_queue_for_task(task_name)
        assert queue_name in managed_queues, schedule_name
