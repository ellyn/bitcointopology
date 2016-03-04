# Markus Salasoo ms933
# CS 5437
# Multiprocessing demo
#
# run with: python multi.py
# in separate terminal/screen, run: ps -ef | grep py
# to see process IDs and parent ID
#
# should see 4 instances of "python multi.py"
# parent, my_service, worker_1, worker_1
#
# referenced https://pymotw.com/2/multiprocessing/basics.html

import multiprocessing
import time

def worker():
    name = multiprocessing.current_process().name
    for i in range(10):
        print name, ' Blink'
        time.sleep(2)
    print name, 'Exiting'

def my_service():
    name = multiprocessing.current_process().name
    for i in range(5):
        print name, ' Blink****'
        time.sleep(5)
    print name, 'Exiting'

if __name__ == '__main__':
    service = multiprocessing.Process(name='my_service', target=my_service)
    worker_1 = multiprocessing.Process(name='worker 1', target=worker)
    worker_2 = multiprocessing.Process(target=worker) # use default name

    worker_1.start()
    worker_2.start()
    service.start()
