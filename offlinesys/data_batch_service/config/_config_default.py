#!/usr/bin/env python
# -*- coding: utf-8 -*-
# _config_default.py
import logging
configs = {
    'db': {
        'host': '10.10.139.235',
        'port': 3306,
        'user': 'iwant',
        'password': 'iwant@201506',
        'database': 'iwant'
    },
    'scheduler': 'default',#default;multi_thread
    'processor': {
        'attr_name_normalize':'default',
        'attr_value_format':'default',
        'attr_value_normalize':'default',
        'merge':'default'
    },
    'log':{
        'log_path':"./logs/%s.log",
        'log_dir':"./logs",
        'error_log_path':"./error_logs/%s_error.log",
        'error_log_dir':"./error_logs",
        'log_level':logging.INFO
    }

}