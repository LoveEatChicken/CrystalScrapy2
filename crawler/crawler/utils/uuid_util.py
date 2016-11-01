# -*- coding: utf-8 -*-
import time
import uuid


def next_id(t=None):
    """
    生成一个唯一id   由 当前时间 + 随机数（由伪随机数得来）拼接得到
    """
    if t is None:
        t = time.time()
    return '%015d%s000' % (int(t * 1000), uuid.uuid4().hex)