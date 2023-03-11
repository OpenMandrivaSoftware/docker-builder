#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psutil
import time

def get_ldd_pid():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'ldd':
            print(proc.info['pid'])
            return proc.info['pid']
    return None

def monitor_ldd():
    ldd_pid = get_ldd_pid()
    while True:
        time.sleep(60)
        new_ldd_pid = get_ldd_pid()
        if new_ldd_pid == ldd_pid:
            if ldd_pid is not None:
                p = psutil.Process(ldd_pid)
                print("killed: {}".format(ldd_pid))
                p.kill()
        else:
            ldd_pid = new_ldd_pid

if __name__ == '__main__':
    monitor_ldd()
