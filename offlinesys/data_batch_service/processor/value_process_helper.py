#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rules import rules
from rules.clean_func_sets import RecognizeHelper
from rules.clean_func_sets import FormatHelper

def format(attr_name,attr_value,raw_data):
    '''
    字段值格式化
    :param attr_name:
    :param attr_value:
    :param raw_data:
    :return:
    '''
    map = rules.get_data_clean_rule(raw_data.template_id)
    if not map:
        result = []
        result.append(attr_value)
        return result
    if not map.has_key(attr_name):
        result = []
        result.append(attr_value)
        return result
    for rule in map[attr_name]:
        if _is_in_rule(attr_value,rule):
            return _clean_with_rule(attr_value, rule)

    return []

def _is_in_rule(value,rule):
    if rule['recognize_rule_type'] is 0:
        func_name = rule['recognize_rule']
        return getattr(RecognizeHelper,func_name)(value)
    else:
        #TODO 待补充其他类型的规则
        return False

def _clean_with_rule(value, rule):
    if rule['clean_rule_type'] is 0:
        func_name = rule['clean_rule']
        return getattr(FormatHelper, func_name)(value)
    else:
        # TODO 待补充其他类型的规则
        return False

def normalize(attr_name,attr_value,raw_data):
    '''
    同义词替换
    :param attr_name:
    :param attr_value:
    :param raw_data:
    :return:
    '''
    map = rules.get_synonym_replaced_rule(raw_data.template_id)
    if not map.has_key(attr_name):
        return attr_value

    values = attr_value.split(" ")
    thesaurus = map[attr_name]
    result = []
    for value in values:
        if thesaurus.has_key(value):
            result.append(thesaurus[value])
        else:
            result.append(value)
