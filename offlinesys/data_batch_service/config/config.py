#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration
"""

from utils.collections import Dict

import _config_default


def merge(defaults, override):
    """
    合并override 和 default 配置文档，返回字典
    """
    r = {}
    for k, v in defaults.iteritems():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r


def toDict(d):
    """
    将一个字典对象转换成 一个Dict对象
    """
    D = Dict()
    for k, v in d.iteritems():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

configs = _config_default.configs



try:
    import _config_override
    configs = merge(configs, _config_override.configs)
except ImportError:
    pass

configs = toDict(configs)



