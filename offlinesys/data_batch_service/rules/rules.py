#!/usr/bin/env python
# -*- coding: utf-8 -*-
from utils import db
import json
from utils import log_util

#映射字典
_schema_map_dict = {}

#必填 item 列 字典
_attr_must_have_map_dict = {}

#value_format字典
_data_clean_map_dict = {}

#value_normalize 字典
_synonym_replaced_map_dict = {}

#核心集字段list
_core_sets=['name','series','brand']

#merge 字典
_merge_dict = {'item_id': 'merge_item_id',
               'name': 'merge_name',
               'en_name': 'merge_en_name',
               'series': 'merge_series',
               'function': 'merge_function',
               'composition': 'merge_composition',
               'color': 'merge_color',
               'smell': 'merge_smell',
               'suitable_skin': 'merge_suitable_skin',
               'texture': 'merge_texture',
               'classify': 'merge_classify',
               'gender': 'merge_gender',
               'age': 'merge_age',
               'usage': 'merge_usage',
               'material': 'merge_material',
               'shelf_life': 'merge_shelf_life',
               'sku_id': 'merge_sku_id',
               'brand_origin': 'merge_brand_origin',
               'brand_en_name': 'merge_brand_en_name'
               }


def init_rules():
    '''
    从rule 摘要表初始化 状态为启用的rules
    :return:
    '''
    pass

def get_merge_dict():
    '''
    获取需要Merge的字段以及对应的处理函数的dict
    :return:
    '''
    return _merge_dict

def get_core_sets():
    '''
    获取核心集字段,用于唯一识别item
    :return:
    '''
    return _core_sets


def get_schema_map(template_id):
    '''
    获取attr_name_map
    :param template_id:
    :return:
    '''
    global _schema_map_dict

    if _schema_map_dict.has_key(template_id):
        return _schema_map_dict[template_id]
    else:
        sql = 'select target_attr_name,source_attr_name from des_schema_map where template_id =?'
        results = db.select(sql,template_id)
        if not results:
            log_util.error('rules.py::get_schema_map():: des_schema_map '
                           'table no data')
            raise RulesException('des_schema_map no data ')
        schema_map = {}
        for result in results:
            schema_map[result.source_attr_name] = result.target_attr_name.strip()
        _schema_map_dict[template_id] = schema_map
        return _schema_map_dict[template_id]

def get_attr_must_have_list(template_id):
    '''
    获取attr_name_not_null_map

    :param template_id:
    :return:
    '''
    global _attr_must_have_map_dict

    if _attr_must_have_map_dict.has_key(template_id):
        return _attr_must_have_map_dict[template_id]
    else:
        map_ids = db.select_one('select attr_must_have from des_template where id = ?',template_id)
        if not map_ids:
            log_util.error('rules.py::get_attr_name_map():: template table no template_id row::id = '+str(template_id))
            _attr_must_have_map_dict[template_id] = []
            return _attr_must_have_map_dict[template_id]
        if not map_ids.attr_must_have:
            log_util.error('rules.py::get_attr_name_map():: template table no template_id row::id = ' + str(template_id))
            _attr_must_have_map_dict[template_id] = []
            return _attr_must_have_map_dict[template_id]
        _attr_must_have_map_dict[template_id] = json.loads(map_ids.attr_must_have)
        return _attr_must_have_map_dict[template_id]

def get_data_clean_rule(template_id):
    '''
    获取value_format_rules
    :param template_id:
    :return:
    '''
    global _data_clean_map_dict

    if _data_clean_map_dict.has_key(template_id):
        return _data_clean_map_dict[template_id]
    else:
        cursor = db.select_one('select data_clean_rules from des_template where id = ?',template_id)
        if not cursor:
            log_util.error('rules.py::get_data_clean_rule():: template table no template_id row::id = '+str(template_id))
            # raise RulesException('cursor None')
            _data_clean_map_dict[template_id] = None
            return _data_clean_map_dict[template_id]
        if not cursor.data_clean_rules:
            log_util.error('rules.py::get_data_clean_rule():: template table no template_id row::id = ' + str(template_id))
            # raise RulesException('cursor.data_clean_rules None')
            _data_clean_map_dict[template_id] = None
            return _data_clean_map_dict[template_id]
        data_clean_rules = json.loads(cursor.data_clean_rules)
        results = {}
        for rule in data_clean_rules:
            sql = 'select * from des_data_clean_rules where id in (' \
                  + db.format_with_separator(rule['rules_ids']) + ')'
            clean_rules = db.select(sql)
            if not clean_rules:
                log_util.error('rules.py::get_data_clean_rule():: data_clean_rules '
                               'table no id row::id = ' + rule['rules_ids'])
                raise RulesException('data_clean_rules no ids ')

            results[rule['path']] = []
            for item in clean_rules:
                if item['recognize_rule_type'] is 0:
                    sql = 'select * from des_func_sets where id = '+ item['recognize_rule']
                    func = db.select_one(sql)
                    item['recognize_rule'] = func.func_name
                if item['clean_rule_type'] is 0:
                    sql = 'select * from des_func_sets where id = ' + item['clean_rule']
                    func = db.select_one(sql)
                    item['clean_rule'] = func.func_name
                results[rule['path']].append(item)

        _data_clean_map_dict[template_id] = results
        return _data_clean_map_dict[template_id]

def get_synonym_replaced_rule(template_id):
    '''
    获取value_normalize_rules
    :param template_id:
    :return:
    '''
    global _synonym_replaced_map_dict

    if _synonym_replaced_map_dict.has_key(template_id):
        return _synonym_replaced_map_dict[template_id]
    else:
        cursor = db.select_one('select synonym_replace_rules from des_template where id = ?',template_id)
        if not cursor:
            log_util.error('rules.py::get_synonym_replaced_rule():: template table no template_id row::id = '+str(template_id))
            # raise RulesException('cursor None')
            _synonym_replaced_map_dict[template_id] = None
            return _synonym_replaced_map_dict[template_id]

        if not cursor.synonym_replace_rules:
            log_util.error('rules.py::get_synonym_replaced_rule():: template table no template_id row::id = ' + str(template_id))
            # raise RulesException('cursor.synonym_replace_rules None')
            _synonym_replaced_map_dict[template_id] = None
            return _synonym_replaced_map_dict[template_id]
        synonym_replace_rules = json.loads(cursor.synonym_replace_rules)
        results = {}
        for rule in synonym_replace_rules:
            result = {}
            sql = "select target_word,synonym from des_synonym_dict where synonym_table_id = ?"
            thesaurus = db.select(sql,rule['synonym_table_id'])
            if not thesaurus:
                log_util.error('rules.py::get_synonym_replaced_rule():: des_synonym_dict '
                               'table no row ')
                raise RulesException('des_synonym_dict no row ')
            for word_pair in thesaurus:
                synonyms = json.loads(word_pair['synonym'])
                for synonym in synonyms:
                    result[synonym]=word_pair['target_word']
            results[rule['path']] = result
        _synonym_replaced_map_dict[template_id] = results
        return _synonym_replaced_map_dict[template_id]


class RulesException(Exception):
    pass


