#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import logging.handlers
from config.config import configs
import socket
import fcntl
import struct
import os

_log = None
_error_log = None

def init_log():
    global _log,_error_log
    file_basename = configs.log.log_path % get_ip_address("eth0")
    if not os.path.exists(configs.log.log_dir):
        os.makedirs(configs.log.log_dir)
    l_handler = logging.handlers.TimedRotatingFileHandler(file_basename, when='D', interval=1,
                                                          backupCount=0)
    l_handler.suffix = "%Y-%m-%d"
    l_formatter = logging.Formatter('[%(asctime)s - %(name)s - ] \t%(message)s')  # 实例化formatter
    l_handler.setFormatter(l_formatter)  # 为handler添加formatter

    _log = logging.getLogger("log")
    _log.addHandler(l_handler)  # 为logger添加handler
    _log.setLevel(configs.log.log_level)

    file_basename = configs.log.error_log_path % get_ip_address("eth0")
    if not os.path.exists(configs.log.error_log_dir):
        os.makedirs(configs.log.error_log_dir)
    e_handler = logging.handlers.TimedRotatingFileHandler(file_basename, when='D', interval=1,
                                                          backupCount=0)
    e_handler.suffix = "%Y-%m-%d"
    e_formatter = logging.Formatter('[%(asctime)s - %(name)s - ] \t%(message)s')  # 实例化formatter
    e_handler.setFormatter(e_formatter)  # 为handler添加formatter

    _error_log = logging.getLogger("error_log")
    _error_log.addHandler(e_handler)  # 为logger添加handler
    _error_log.setLevel(logging.ERROR)

def info(msg, *args, **kwargs):
    _log.info(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    _log.debug(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    _log.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    _error_log.error(msg, *args, **kwargs)

def log(func):
    def wrapper(*args, **kw):
        info('call %s():' % func.__name__)
        return func(*args, **kw)
    return wrapper

'''
    获取网口对应的IP(V4)地址
'''
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]) )[20:24])