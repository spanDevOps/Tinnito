import redis
from rq import Worker, Queue, Connection
import os
import sys

listen = ['default']

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(['default'])
        worker.work()
