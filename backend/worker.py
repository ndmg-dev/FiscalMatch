import os
from redis import Redis
from rq import Worker, Queue, Connection
from app.core.config import settings

listen = ['default']
redis_url = os.getenv('REDIS_URL', settings.REDIS_URL)
conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
