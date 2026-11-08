"""Serialize all container writers, including independent manual and scheduled Jobs."""
import os
import signal
import subprocess
import sys

import redis


def main():
    url = os.getenv('REDIS_URL') or (
        f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/0")
    client = redis.Redis.from_url(url, socket_timeout=5, socket_connect_timeout=5)
    # Outside rahbar:cache:* so the pipeline's cache invalidation cannot erase it.
    lock = client.lock('rahbar:indexer:writer', timeout=120, blocking=False)
    child = None
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True
        if child is not None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if not lock.acquire():
        print('writer lock held: refusing concurrent indexing', flush=True)
        return 75
    try:
        child = subprocess.Popen([sys.executable, '-m', 'pipeline.run', *sys.argv[1:]])
        while True:
            try:
                return child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if stopped:
                    return 143
                # Redis errors/ownership loss fail closed, terminating the writer
                # well before the 120-second lease could permit another writer.
                lock.extend(120, replace_ttl=True)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        if lock.owned():
            lock.release()
        client.close()


if __name__ == '__main__':
    sys.exit(main())
