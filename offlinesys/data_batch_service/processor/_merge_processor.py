#!/usr/bin/env python
# -*- coding: utf-8 -*-

from processor import _BaseProcessor
from config.config import configs
from rules import rules
import json
from utils import db
import collections
from utils import math
from rules.merge_func_sets import MergeHelper

class _MergeProcessor(_BaseProcessor):
    '''
    属性名归一化处理器,基类
    '''
    @staticmethod
    def get_instance(task_info):
       type =  configs.processor.merge
       if type == 'default':
           return _DefaultMergeProcessor(task_info)



class _DefaultMergeProcessor(_MergeProcessor):
    '''
    默认属性名归一化处理器,单线程执行
    '''
    def do_process(self):
        data_map = self.get_value_checked_data_map(self._task_info)
        if not data_map:
            return False
        item_map = self.get_item_data()
        merge_map = rules.get_merge_dict()
        results = []
        for k,v in data_map:
            result = collections.OrderedDict()
            for k1,v1 in merge_map:
                func_name = v1
                if item_map.has_key(k):
                    item = item_map[k]
                else:
                    item = None
                result = getattr(MergeHelper, func_name)(v,item,result)
            results.append(result)
        self.save_data(results)

    def save_data(self, items):
        if not items:
            return
        with db.transaction():
            for item in items:
                sql = "replace into des_raw_entity (" + db.format_with_separator(
                    item.iterkeys()) + ") values ("
                l = []
                for i in range(0, len(item.keys())):
                    l.append('?')
                sql = sql + db.format_with_separator(l) + ")"
                db.update(sql, *item.values())


    def calculate_item_id(self,data):
        '''
        依靠核心集计算data的item_id
        :param data:
        :return:
        '''
        core_sets = rules.get_core_sets()
        str = ""
        for set in core_sets:
            if data['content'][set]:
                str+=data['content'][set]
        if str:
            return math.md5(str)
        else:
            return ''

    def get_value_checked_data_map(self, task_info):
        '''
        目前data filter只支持site
        :param task_info:
        :return:
        '''
        # TODO 丰富对datafilter的支持力度

        filter = json.loads(task_info.data_filter)
        sql = "select * from des_struct_data_manual_checked where (exception_code = 0) and (site = '" \
                  + filter['site'] + "')"
        datas = db.select(sql)

        if not datas:
            return None
        map = {}
        for data in datas:
            item_id = self.calculate_item_id(data)
            if not map.has_key(item_id):
                list = []
                list.append(data)
                map[item_id] = list
            else:
                map[item_id] = map[item_id].append(data)
        return map

    def get_item_data(self):
        sql = "select * from des_item"
        items = db.select(sql)
        if not items:
            return None
        map = {}
        for item in items:
            map[item.item_id]= item
        return map




