#!/usr/bin/env python
# encoding=utf-8
""""
bin/qasearch.py
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")


def sql_row2json(row):
    """
    sql转成json
    """
    if len(row) < 10:
        return None
    obj = dict()
    obj["doc_id"] = row[0]
    obj["query"] = row[1]
    obj["question"] = row[2]
    obj["answer"] = row[3]
    obj["domain"] = row[4]
    obj["classify"] = row[5]
    obj["category"] = row[6]
    obj["source"] = row[7]
    # obj["create_time"] = row[8]
    # obj["update_time"] = row[9]
    return obj


def run(conf, db_all):
    """
    处理数据库一次性扫除来的数据
    返回最终要建库的数据
    """
    doc_list = list()
    for row in db_all:
        obj = sql_row2json(row)
        if obj is not None:
            doc_list.append(obj)
    return doc_list


def main():
    print 'run main func'

if __name__ == '__main__':
    main()
