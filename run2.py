from concurrent.futures import ThreadPoolExecutor
import threading
from subprocess import Popen, PIPE
import logging

logging.basicConfig(level='INFO')
def dpy_run():
	process = Popen(['py', 'dpy_run.py'], stdout=PIPE, stderr=PIPE)
	stdout, stderr = process.communicate()
	print(stdout)

def hikari_run():
	process = Popen(['py', 'hikari_run.py'], stdout=PIPE, stderr=PIPE)
	stdout, stderr = process.communicate()
	print(stdout)


def main():
    executor = ThreadPoolExecutor(max_workers=3)
    task1 = executor.submit(dpy_run)
    task2 = executor.submit(hikari_run)

if __name__ == '__main__':
    main()