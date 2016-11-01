#!/usr/bin/env python
# coding: utf-8

import re
import string

class Parse_Util:

    @staticmethod
    #获取无id、无序标签内容
    def get_parse_value(parentControl, parseKey):
        value = 'None'

        for li in parentControl.children:

            if li.string == None:
                li.string = re.sub(re.compile('\s+'), '', li.text)
            if li.string == None:
                continue
            if re.match(r'\s+', li.string):
                continue
            # print 'li_string ---------- %s' % li.string
            if hasattr(li.string, 'strip'):
                p = re.compile('\s+')
                no_space_string = re.sub(p, '', li.string)
                no_space_string = '%s%s' % (no_space_string, ' ')
                # print 'no_space_string ---------- %s' % no_space_string
                if no_space_string.strip().startswith(parseKey):
                    # print 'parserKey ---------------- %s' % parseKey
                    value = no_space_string.strip(parseKey)
                    # print 'value ------------- %s' % value

        return value

    @staticmethod
    #构造归一化字典
    def make_up_dic(parentControl):
        dic = {}
        # print 'ttttttttttt ----- %s' % type(parentControl)
        # print 'aaaaaaaaaaa ----- %s' % parentControl
        # print 'liiiiiiiiiiiii --------- %s' % parentControl.stripped_strings
        for li_str in parentControl.stripped_strings:
            # print 'liiiiistr --------- %s' % li_str
            if string.find(li_str, u'：')!= -1 and li_str[-1] != u'：':
            # print 'liiiiistr --------- %s ----laststr ------%s' % (li_str, li_str[-1])
                p = re.compile('\s+')
                no_space_string = re.sub(p, '', li_str)
                # print 'ssssssssssss %s' % no_space_string
                parameterList = no_space_string.split(u'：')
                dic[parameterList[0]] = parameterList[1]

        # print dic
        return dic

    @staticmethod
    #获取url域名
    def get_source_origin(url):
        m = re.match(r'((https|http)://\w+.)([\s\S]*)(/)', url)

        return m.group(3)

    @staticmethod
    #获取Json串
    def get_json_str(response_data):
        m = re.match(r'([jQuery0-9]+\()([\s\S]*)(\);)', response_data)

        return m.group(2)
    @staticmethod
    #删除标签中某个子属性
    def delete_node_content(parentControl, node):
        modified_value = parentControl.text

        del_node = parentControl.find(node)
        modified_value = parentControl.text.strip(del_node.string)

        return modified_value

    @staticmethod
    #获取无子标签tag":"后的Value
    def get_parse_text_value(tag, parseKey):
        value = 'None'
        # print 'zzzzzzzzzzz ------------ %s' % tag.text
        if hasattr(tag.text, 'strip'):
            p = re.compile('\s+')
            no_space_string = re.sub(p, '', tag.text)
            if no_space_string.strip().startswith(parseKey):
                value = no_space_string.strip(parseKey)

        return value

    @staticmethod
    #获取无空格String
    def get_no_space_string(origin_str):

        no_space_string = origin_str.replace("\t", " ").replace("\n", " ").replace("\r", " ").strip()
        no_space_string = " ".join(no_space_string.split())
        return no_space_string

    @staticmethod
    def structure_parameter_dic(info_tags, decollator):
        pro_parameter_dic = {}

        for info_tag in info_tags:
            # print 'ttttttttttttttt ----------------- %s' % info_tag
            no_space_string = info_tag.text.replace("\t", " ").replace("\n", " ").replace("\r", " ").strip()
            no_space_string = " ".join(no_space_string.split())

            if string.find(no_space_string, decollator)!= -1 and no_space_string[-1] != decollator:
                parameterList = no_space_string.split(decollator)
                pro_parameter_dic[parameterList[0]] = parameterList[1]

        # print 'zzzzzzzzzsssssssssssss -------------- %s' % dic
        return pro_parameter_dic

