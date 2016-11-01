#!/usr/bin/env python
# -*- coding: utf-8 -*-

from processor import _BaseProcessor
from config.config import configs
import json
from utils import db
from rules import rules
import collections
from utils.log_util import log


class _AttrNameNormalizeProcessor(_BaseProcessor):
    '''
    属性名归一化处理器,基类
    '''

    @staticmethod
    def get_instance(task_info):
        type = configs.processor.attr_name_normalize
        if type == 'default':
            return _DefaultAttrNameNormalizeProcessor(task_info)


class _DefaultAttrNameNormalizeProcessor(_AttrNameNormalizeProcessor):
    '''
    默认属性名归一化处理器,单线程执行
    '''
    page_limit = 500

    @log
    def process(self):
        for skus in self.sku_data_generator(self._task_info):
            items = self.convert_item_name(skus)
            self.save_data(items)
        return True

    def sku_data_generator(self, task_info):
        '''
        目前data filter只支持site
        :param task_info:
        :return:
        '''

        # TODO 丰富对datafilter的支持力度
        size = _DefaultAttrNameNormalizeProcessor.page_limit
        filter = json.loads(task_info.data_filter)
        last_id = '0'

        while size == _DefaultAttrNameNormalizeProcessor.page_limit:

            sql = "select id,content,url,source,site,template_id,classify,subclass,domain " \
                  "from des_raw_parsed_data where (id > '" \
                  + last_id + "') and (exception_code = 0) and (site = '"\
                  + filter['site'] + "') order by id asc limit 0," \
                  + str(_DefaultAttrNameNormalizeProcessor.page_limit)
            result = db.select(sql)
            size = len(result)
            if size > 0:
                last_id = result[size - 1].id
            yield result

    # def convert_item_name2(self, skus):
    #     if not skus:
    #         return
    #     result = []
    #     for sku in skus:
    #         item = collections.OrderedDict()
    #
    #         sku.content = json.loads(sku.content)
    #         item.update(self.convert(sku, item))
    #         item = self.check_exception(item,sku.template_id)#异常检查
    #         result.append(item)
    #     return result

    def convert_item_name(self, skus):
        if not skus:
            return
        result = []
        for sku in skus:
            item = collections.OrderedDict()
            for k, v in sku.iteritems():
                item[k] = v
            sku.content = json.loads(sku.content)
            name_map = rules.get_schema_map(sku.template_id)
            not_null_list = rules.get_attr_must_have_list(sku.template_id)
            exception_code = 0
            exception_detail = {}
            item['content'] = {}
            item['content'],exception_code,exception_detail = \
                self.convert(sku.content, item['content'],name_map,exception_code,exception_detail,not_null_list)
            # item = self.check_exception(item, sku.template_id)  # 异常检查
            item['content'] = json.dumps(item['content'],ensure_ascii=False)
            item['exception_code'] = exception_code
            item['exception_detail'] = json.dumps(exception_detail, ensure_ascii=False)
            result.append(item)
        return result


    def convert(self, sku, item,name_map,exception_code,exception_detail,not_null_list):
        for k, v in sku.iteritems():
            key = self.map_key(k, name_map)
            if not key:
                continue
            if isinstance(v, dict):
                item[key] = {}
                item[key],exception_code,exception_detail = self.convert(v, item[key],name_map,exception_code,exception_detail,not_null_list)
            else:
                item[key] =v
                if (v is None) or (v == ""):
                    exception_detail[key] = "None"
                    if key in not_null_list:
                        exception_code = 2
                    elif exception_code!=2 :
                        exception_code = 1
        return item,exception_code,exception_detail

    def map_key(self,key,key_map):
        if key_map.has_key(key):
            return key_map[key]
        else:
            return None


    @log
    def save_data(self, items):
        if not items:
            return
        with db.transaction():
            for item in items:
                sql = "replace into des_schema_mapped (" + db.format_with_separator(
                    item.iterkeys()) + ") values ("
                l = []
                for i in range(0, len(item.keys())):
                    l.append('?')
                sql = sql + db.format_with_separator(l) + ")"

                db.update(sql, *item.values())

