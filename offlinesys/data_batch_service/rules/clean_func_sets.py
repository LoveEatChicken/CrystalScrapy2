#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re


class RecognizeHelper(object):
    '''
    识别Helper
    '''

    @staticmethod
    def test(value):
        return value

    @staticmethod
    def rec_name( value):
        print "rec_name value = " + value
        return True

    @staticmethod
    def rec_percent(value):
        print "rec_percent value = " + value
        pattern = re.compile('\d{1,2}\%{1}$')
        result = re.match(pattern, value)
        if result:
            return True
        else:
            return False

    @staticmethod
    def rec_english(value):
        print "rec_english value = " + value
        pattern = re.compile('[a-zA-Z]+$')
        result = re.match(pattern, value)
        if result:
            return True
        else:
            return False




class FormatHelper(object):
    '''
    格式化helper
    '''

    @staticmethod
    def test( value):
        return [value,]

    @staticmethod
    def clean_name( value):
        print "clean_name value = " + value

        return [value,]

    @staticmethod
    def convert_percent2int(value):
        print "convert_percent2int value = " + value
        value = value.replace('%', '')
        value = round(float(value) / 20)
        return [value,]

    @staticmethod
    def convert2lower_case(value):
        print "convert2lower_case value = " + value
        return [value.lower(),]
