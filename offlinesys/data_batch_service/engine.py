#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scheduler import OnScheduleListener
from scheduler import SchedulerFactory
from scheduler import BaseScheduler
from task import TaskHelper
from rules import rules
import sys
from utils import db
from config import config
from utils import log_util
from utils.log_util import log


class Engine(OnScheduleListener):
    '''
    批处理控制引擎
    '''

    def __init__(self):
        log_util.init_log()
        user = config.configs['db']['user']
        pw = config.configs['db']['password']
        host = config.configs['db']['host']
        port = config.configs['db']['port']
        database = config.configs['db']['database']
        db.create_engine(user,pw,database,host,port)
        self.scheduler = None


    @log
    def init(self):
        '''
        初始化
        '''
        rules.init_rules()



    @property
    def scheduler(self):
        return self.__scheduler
    @scheduler.setter
    def scheduler(self,value):
        if (value is None) or isinstance(value, BaseScheduler):
            self.__scheduler = value
        else:
            raise ValueError('value must be a BaseScheduler!')

    @log
    def start(self,tasks):
        '''
        启动
        :return:
        '''

        if not tasks:
            return
        if self.scheduler is None:
            scheduler = SchedulerFactory.create_instance()  # 创建调度器
            scheduler.tasks=tasks
            # scheduler.set_callback(self)
            self.scheduler = scheduler
            self.scheduler.start()
        else:
            #TODO 任务进行中,增加任务的逻辑
            pass
        #TODO 锁住当前线程,等待任务执行完成



    def on_start(self):
        pass

    def on_finish(self):
        #TODO 解锁当期线程,结束进程
        pass




def _main():
    args = sys.argv
    if len(args) < 2:
        sys.exit()
    engine = Engine()
    with db.connection():#建立连接
        tasks = TaskHelper.init_tasks_from_db(args[1:])
        if not tasks:
            sys.exit()
        engine.init()
        engine.start(tasks)
        print 'Success !!!!'

if __name__ == '__main__':
    _main()