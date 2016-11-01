#!/usr/bin/env python
# encoding=utf-8
""""
fmsearch.py
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import logging
import json


def sql_row2json(row):
    """
    sql转成json
    """
    if len(row) < 2:
        logging.warning("sql error , row not valid array")
        return None

    obj = json.loads(row[1])
    obj["doc_id"] = row[0]

    return obj


def run(conf, db_all):
    """
    处理数据库一次性扫除来的数据
    返回最终要建库的数据
    """
    doc_list = list()
    try:
        for row in db_all:
            obj = sql_row2json(row)
            if obj is not None:
                doc_list.append(obj)
        return doc_list
    except Exception as e:
        logging.warning(e)
        return None



def main():
    print 'run main func'

if __name__ == '__main__':
    main()
