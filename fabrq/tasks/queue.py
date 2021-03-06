import os
import subprocess

from invoke import task
from redis import Redis
from rq import Queue
from rq.registry import (FailedJobRegistry, FinishedJobRegistry,
                         StartedJobRegistry)

try:
    REDIS_HOST = os.environ["REDIS_HOST"]
except:
    print("Environment variables should contain REDIS_HOST")
try:
    REDIS_PORT = os.environ["REDIS_PORT"]
except:
    print("Environment variables should contain REDIS_PORT")
try:
    REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]
except:
    print("Environment variables should contain REDIS_PASSWORD")
try:
    REDIS_DB = os.environ["REDIS_DB"]
except:
    print("Environment variables should contain REDIS_DB")
try:
    REDIS_URL = os.environ["REDIS_URL"]
except:
    print("Environment variables should contain REDIS_URL")


def subprocess_cmd(cmd):
    print("Launch {}".format(cmd))

    try:
        subprocess.check_output("{}".format(cmd), shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "Command '{}' return with error (code {}): {}".format(
                e.cmd, e.returncode, e.output
            )
        )
    return 0


@task
def cmd(c, queue=None, cmd="sleep 100"):
    """Enqueue cmd to given queue, executed as a subprocess
    """
    if queue is None:
        raise ValueError("Please specify queue")

    q = Queue(
        queue,
        connection=Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB
        ),
    )

    _ = q.enqueue(
        subprocess_cmd, cmd, job_timeout=-1, ttl=None, result_ttl=-1, failure_ttl=-1,
    )


@task
def delete_started(c, queue=None):
    """Delete started jobs from given queue
    """
    if queue is None:
        raise ValueError("Please specify queue")

    q = Queue(
        queue,
        connection=Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB
        ),
    )
    registry = StartedJobRegistry(queue=q)
    for job_id in registry.get_job_ids():
        job = q.fetch_job(job_id)
        if job is not None and job.is_started:
            job.delete()

@task
def delete_finished(c, queue=None):
    """Delete finished jobs from given queue
    """
    if queue is None:
        raise ValueError("Please specify queue")

    q = Queue(
        queue,
        connection=Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB
        ),
    )
    registry = FinishedJobRegistry(queue=q)
    for job_id in registry.get_job_ids():
        job = q.fetch_job(job_id)
        if job is not None and job.is_started:
            job.delete()


@task
def delete_failed(c, queue=None):
    """Delete failed jobs from given queue
    """
    if queue is None:
        raise ValueError("Please specify queue")

    q = Queue(
        queue,
        connection=Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB
        ),
    )
    r = FailedJobRegistry(queue=q)
    for job_id in r.get_job_ids():
        job = q.fetch_job(job_id)
        if job.is_failed:
            job.delete()


@task
def delete_queue(c, queue=None):
    """Delete given queue
    """
    if queue is None:
        raise ValueError("Please specify queue")

    delete_started(c, queue=queue)
    delete_finished(c, queue=queue)
    delete_failed(c, queue=queue)

    q = Queue(
        queue,
        connection=Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB
        ),
    )
    q.delete()


@task
def requeue_started(c, queue=None):
    """Requeue started jobs from given queue
    """
    if queue is None:
        raise ValueError("Please specify queue")

    q = Queue(
        queue,
        connection=Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB
        ),
    )
    registry_started = StartedJobRegistry(queue=q)
    registry_failed = FailedJobRegistry(queue=q)

    for job_id in registry_started.get_job_ids():
        job = q.fetch_job(job_id)
        if job is not None and job.is_started:
            registry_started.remove(job)
            registry_failed.add(job, ttl=job.failure_ttl,
                exc_string="Started job moved for requeuing")
            job.requeue()


@task
def requeue_failed(c, queue=None):
    """Requeue started jobs from given queue
    """
    if queue is None:
        raise ValueError("Please specify queue")

    q = Queue(
        queue,
        connection=Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_DB
        ),
    )
    registry = FailedJobRegistry(queue=q)
    for job_id in registry.get_job_ids():
        job = q.fetch_job(job_id)
        if job is not None:
            job.requeue()
