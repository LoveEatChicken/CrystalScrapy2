#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import log_util
import traceback


class _BaseProcessor(object):
    '''
    处理器基类
    '''

    def __init__(self,task_info):
        self._task_info = task_info


    def do_process(self):
        '''
        处理函数,同步函数
        :return:
        '''
        try:
            return self.process()
        except:
            traceback.print_exc()
            log_util.error(traceback.format_exc())
            return False

    def process(self):
        pass



class ProcessorFactory(object):
    '''处理器工厂'''

    @staticmethod
    def create_instance(task_info):
        '''
        工厂方法,创建实例
        从配置文件
        processor中的配置,初始化实例类型
        '''
        from _attr_name_processor import _AttrNameNormalizeProcessor
        from _attr_value_processor import _AttrValueCleanProcessor
        from _attr_value_processor import _AttrValueSynonymReplaceProcessor
        from _merge_processor import _MergeProcessor
        from _test_processor import _EntityFillProcessor
        from _test_processor import _StructDataFillProcessor

        if task_info.cmd == 1:
            return _AttrNameNormalizeProcessor.get_instance(task_info)
        if task_info.cmd == 2:
            return _AttrValueCleanProcessor.get_instance(task_info)
        if task_info.cmd == 3:
            return _AttrValueSynonymReplaceProcessor.get_instance(task_info)
        if task_info.cmd == 4:
            return _MergeProcessor.get_instance(task_info)
        if task_info.cmd == 5:
            return _EntityFillProcessor.get_instance(task_info)
        if task_info.cmd == 6:
            return _StructDataFillProcessor.get_instance(task_info)
        return None