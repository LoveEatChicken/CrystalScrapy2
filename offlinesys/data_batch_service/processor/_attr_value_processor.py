#!/usr/bin/env python
# -*- coding: utf-8 -*-

from processor import _BaseProcessor
from config.config import configs
from utils.log_util import log

import json
from utils import db
import collections
import value_process_helper
from rules import rules

class _AttrValueSynonymReplaceProcessor(_BaseProcessor):
    '''
    属性值同义词替换处理器,基类
    '''
    @staticmethod
    def get_instance(task_info):
       type =  configs.processor.attr_value_normalize
       if type == 'default':
           return _DefaultAttrValueSynonymReplaceProcessor(task_info)



class _DefaultAttrValueSynonymReplaceProcessor(_AttrValueSynonymReplaceProcessor):
    '''
    默认属性值同义词替换处理器,单线程执行
    '''
    page_limit = 500

    @log
    def process(self):
        for skus in self.cleaned_data_generator(self._task_info):
            items = self.process_value(skus)
            self.save_data(items)
        return True

    def cleaned_data_generator(self, task_info):
        '''
        目前data filter只支持site
        :param task_info:
        :return:
        '''

        # TODO 丰富对datafilter的支持力度
        size = _DefaultAttrValueCleanProcessor.page_limit
        filter = json.loads(task_info.data_filter)
        last_id = '0'

        while size == _DefaultAttrValueCleanProcessor.page_limit:

            sql = "select id,content,url,source,site,template_id,classify,subclass,domain from des_data_cleaned where (id > '" \
                  + last_id + "') and (exception_code = 0) and (site = '" \
                  + filter['site'] + "') order by id asc limit 0," \
                  + str(_DefaultAttrValueSynonymReplaceProcessor.page_limit)
            result = db.select(sql)
            size = len(result)
            if size > 0:
                last_id = result[size - 1].id
            yield result

    def process_value(self, skus):
        if not skus:
            return
        result = []
        for sku in skus:
            item = collections.OrderedDict()
            for k, v in sku.iteritems():
                item[k] = v
            exception_code = 0
            exception_detail = {}
            sku.content = json.loads(sku.content)
            map = rules.get_synonym_replaced_rule(sku.template_id)
            item['content'] = {}
            item['content'],exception_code,exception_detail = \
                self.normalize_value(sku.content, item['content'],map,exception_code,exception_detail)
            item['content'] = json.dumps(item['content'],ensure_ascii=False)
            item['exception_code'] = exception_code
            item['exception_detail'] = json.dumps(exception_detail,ensure_ascii=False)
            result.append(item)
        return result

    def normalize_value(self, input, output,map,exception_code,exception_detail,path='/'):
        for k, v in input.iteritems():
            new_path = path + k + "/"
            if isinstance(v, dict):
                output[k] = {}
                output[k], exception_code, exception_detail = \
                    self.normalize_value(v, output[k], map, exception_code, exception_detail, new_path)
            else:
                if (not map) or (not map.has_key(new_path)):
                    output[k] = v
                else:
                    if isinstance(v,list):
                        values = v
                    else:
                        values = []
                        values.append(v)
                    thesaurus = map[new_path]
                    s = []
                    error = {}
                    for value in values:
                        if thesaurus.has_key(value):
                            s.append(thesaurus[value])
                        else:
                            s.append(value)
                            exception_code = 1;
                            error[value]='None'
                    output[k] = s
                    if error:
                        exception_detail[new_path] = error

        return output,exception_code,exception_detail

    @log
    def save_data(self, items):
        if not items:
            return
        with db.transaction():
            for item in items:
                sql = "replace into des_synonym_replaced (" + db.format_with_separator(
                    item.iterkeys()) + ") values ("
                l = []
                for i in range(0, len(item.keys())):
                    l.append('?')
                sql = sql + db.format_with_separator(l) + ")"

                db.update(sql, *item.values())


class _AttrValueCleanProcessor(_BaseProcessor):
    '''
    属性值 格式化 处理器,基类
    '''
    @staticmethod
    def get_instance(task_info):
       type =  configs.processor.attr_value_format
       if type == 'default':
           return _DefaultAttrValueCleanProcessor(task_info)



class _DefaultAttrValueCleanProcessor(_AttrValueCleanProcessor):
    '''
    默认属性值 格式化 处理器,单线程执行
    '''
    page_limit = 500

    @log
    def process(self):
        for skus in self.schema_mapped_data_generator(self._task_info):
            items = self.process_value(skus)
            self.save_data(items)
        return True

    def schema_mapped_data_generator(self, task_info):
        '''
        目前data filter只支持site
        :param task_info:
        :return:
        '''

        # TODO 丰富对datafilter的支持力度
        size = _DefaultAttrValueCleanProcessor.page_limit
        filter = json.loads(task_info.data_filter)
        last_id = '0'

        while size == _DefaultAttrValueCleanProcessor.page_limit:

            sql = "select id,content,url,source,site,template_id,classify,subclass,domain from des_schema_mapped where (id > '" \
                  + last_id + "') and (exception_code = 0) and (site = '"\
                  + filter['site'] + "') order by id asc limit 0," \
                  + str(_DefaultAttrValueCleanProcessor.page_limit)
            result = db.select(sql)
            size = len(result)
            if size > 0:
                last_id = result[size - 1].id
            yield result


    def process_value(self, skus):
        if not skus:
            return
        result = []
        for sku in skus:
            item = collections.OrderedDict()
            for k, v in sku.iteritems():
                item[k] = v
            # item = self.clean_value(sku, item)

            exception_code = 0
            exception_detail = {}
            item['content'] = {}
            sku.content = json.loads(sku.content)
            item['content'],exception_code,exception_detail = \
                self.clean_value(sku.content,sku,item['content'],exception_code,exception_detail)
            item['content'] = json.dumps(item['content'],ensure_ascii=False)
            item['exception_code'] = exception_code
            item['exception_detail'] = json.dumps(exception_detail,ensure_ascii=False)

            result.append(item)
        return result

    def clean_value(self,sku_content, sku, item_content,exception_code,exception_detail,path='/'):

        for k,v in sku_content.iteritems():
            new_path = path+k+"/"
            if isinstance(v, dict):
                item_content[k] = {}
                item_content[k],exception_code,exception_detail = \
                    self.clean_value(v,sku,item_content[k],exception_code,exception_detail,new_path)

            else:
                formated_value = value_process_helper.format(new_path, v, sku)
                if not formated_value:
                    exception_code = 1;
                    exception_detail[new_path] = 'None'
                    item_content[k] = v
                else:
                    item_content[k] = formated_value

        return item_content,exception_code,exception_detail

    def convert2Json(self,v):
        if isinstance(v, basestring):
            return json.dumps(v.split("##"),ensure_ascii=False)
        array = []
        array.append(v)
        return json.dumps(array,ensure_ascii=False)

    @log
    def save_data(self, items):
        if not items:
            return
        with db.transaction():
            for item in items:
                sql = "replace into des_data_cleaned (" + db.format_with_separator(
                    item.iterkeys()) + ") values ("
                l = []
                for i in range(0, len(item.keys())):
                    l.append('?')
                sql = sql + db.format_with_separator(l) + ")"

                db.update(sql, *item.values())

