from celery import shared_task

from application.celery import app


@app.task(acks_late=False)
def task__one(*args, **kwargs):
    print(11111)


@app.task
def task__two(*args, **kwargs):
    print(22222)


@app.task
def task__three(*args, **kwargs):
    print(33333)


@app.task
def task__four(*args, **kwargs):
    print(44444)
