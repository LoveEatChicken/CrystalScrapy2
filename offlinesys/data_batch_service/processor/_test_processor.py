#!/usr/bin/env python
# -*- coding: utf-8 -*-

from processor import _BaseProcessor
import json
from utils import db
import collections

class _EntityFillProcessor(_BaseProcessor):
    page_limit = 500
    '''
    属性名归一化处理器,基类
    '''
    @staticmethod
    def get_instance(task_info):

        return _EntityFillProcessor(task_info)

    def process(self):
        for skus in self.cleaned_data_generator(self._task_info):
            items = self.process_value(skus)
            self.save_data(items)
        return True

    def process_value(self, skus):
        if not skus:
            return
        result = []
        for sku in skus:
            item = collections.OrderedDict()
            for k, v in sku.iteritems():
                item[k] = v
            result.append(item)
        return result

    def save_data(self, items):
        if not items:
            return
        with db.transaction():
            for item in items:
                sql = "replace into des_entities (" + db.format_with_separator(
                    item.iterkeys()) + ") values ("
                l = []
                for i in range(0, len(item.keys())):
                    l.append('?')
                sql = sql + db.format_with_separator(l) + ")"
                db.update(sql, *item.values())

    def cleaned_data_generator(self, task_info):
        '''
        目前data filter只支持site
        :param task_info:
        :return:
        '''

        # TODO 丰富对datafilter的支持力度
        size = _EntityFillProcessor.page_limit
        filter = json.loads(task_info.data_filter)
        last_id = '0'

        while size == _EntityFillProcessor.page_limit:

            sql = "select id,content,classify,subclass,domain from des_synonym_replaced where (id > '" \
                  + last_id + "') and (exception_code = 0) and (site = '" \
                  + filter['site'] + "') order by id asc limit 0," \
                  + str(_EntityFillProcessor.page_limit)
            result = db.select(sql)
            size = len(result)
            if size > 0:
                last_id = result[size - 1].id
            yield result


class _StructDataFillProcessor(_BaseProcessor):
    page_limit = 500
    '''
    属性名归一化处理器,基类
    '''
    @staticmethod
    def get_instance(task_info):

        return _StructDataFillProcessor(task_info)

    def process(self):
        for skus in self.synonym_replaced_generator(self._task_info):
            items = self.process_value(skus)
            self.save_data(items)
        return True

    def process_value(self, skus):
        if not skus:
            return
        result = []
        for sku in skus:
            item = collections.OrderedDict()
            for k, v in sku.iteritems():
                item[k] = v
            result.append(item)
        return result

    def save_data(self, items):
        if not items:
            return
        with db.transaction():
            for item in items:
                sql = "replace into des_struct_data_manual_checked (" + db.format_with_separator(
                    item.iterkeys()) + ") values ("
                l = []
                for i in range(0, len(item.keys())):
                    l.append('?')
                sql = sql + db.format_with_separator(l) + ")"
                db.update(sql, *item.values())

    def synonym_replaced_generator(self, task_info):
        '''
        目前data filter只支持site
        :param task_info:
        :return:
        '''

        # TODO 丰富对datafilter的支持力度
        size = _EntityFillProcessor.page_limit
        filter = json.loads(task_info.data_filter)
        last_id = '0'

        while size == _EntityFillProcessor.page_limit:

            sql = "select id,content,url,source,site,template_id,classify,subclass,domain from des_synonym_replaced where (id > '" \
                  + last_id + "') and (exception_code = 0) and (site = '" \
                  + filter['site'] + "') order by id asc limit 0," \
                  + str(_EntityFillProcessor.page_limit)
            result = db.select(sql)
            size = len(result)
            if size > 0:
                last_id = result[size - 1].id
            yield result


