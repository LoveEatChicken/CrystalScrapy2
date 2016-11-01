#!/usr/bin/env python
# -*- coding: utf-8 -*-
from config import config
from utils.collections import Dict
from processor.processor import ProcessorFactory
from task import BaseTask
from utils.log_util import log

class BaseScheduler(object):
    '''调度器基类,抽象类不可实例化'''

    def __getattr__(self, attr):
        raise AttributeError('Engine object has no attribute %s' % attr)

    @property
    def is_running(self):
        return self.__is_running

    @is_running.setter
    def is_running(self, value):
        self.__is_running = value

    @property
    def tasks(self):
        return self.__tasks

    @tasks.setter
    def tasks(self, value):
        if not isinstance(value, list):
            raise ValueError('task must be a Tasks!')
        self.__tasks = value

    @property
    def callback(self):
        return self.__callback

    @callback.setter
    def callback(self, value):
        if not isinstance(value, OnScheduleListener):
            raise ValueError('callback must be a OnScheduleListener!')
        self.__callback = value

    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = True
        pass


class _DefaultScheduler(BaseScheduler):
    '''默认调度器,单线程顺序执行TASK'''
    @log
    def start(self):
        super(_DefaultScheduler, self).start()
        for task in self.tasks:
            task.start()

    def stop(self):
        super(_DefaultScheduler, self).stop()


class _MultiThreadScheduler(BaseScheduler):
    '''多线程调度器,按group_id分配TASK执行线程'''

    def start(self):
        super(_DefaultScheduler, self).start()
        # TODO
        pass

    def stop(self):
        super(_DefaultScheduler, self).stop()
        # TODO
        pass


class SchedulerFactory(object):
    '''调度器工厂'''

    @staticmethod
    def create_instance():
        '''
        工厂方法,创建实例
        从配置文件
        scheduler中的配置,初始化实例类型
        '''

        type = config.configs.scheduler
        if type == 'multi_thread':
            return _MultiThreadScheduler()
        else:
            return _DefaultScheduler()


class OnScheduleListener(object):
    '''调度器回调'''

    def on_start(self):
        '''调度器启动回调'''
        pass

    def on_finish(self):
        '''调度器全部任务执行完毕回调'''
        pass
