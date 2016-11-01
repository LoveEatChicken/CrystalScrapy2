#!/usr/bin/env python
# -*- coding: utf-8 -*-
from utils.collections import Dict
from rules import rules
from utils import db
import traceback
from utils import log_util
from processor.processor import ProcessorFactory
from utils.log_util import log

class TaskHelper(list):
    '''
    任务帮助类
    '''

    @staticmethod
    def init_tasks_from_db(ids = []):
        '''
        从iwant DB 的des_task表初始化tasks

        :return: Dict list
        '''
        if not ids :
            return None
        sql = 'select * from des_task where (status = 0) and (id in ('
        index = 0
        for id in ids:
            if index == 0:
                sql = sql+id
            else:
                sql = sql +','+id
        sql = sql+'))'
        task_infos = db.select(sql)
        if not task_infos:
            return None
        tasks = []
        for task_info in task_infos:
            task = BaseTask.get_instance(task_info)
            tasks.append(task)
        return tasks

class BaseTask(object):
    '''
    任务基类
    '''
    def __init__(self,task_info):
        self.task_info=task_info

    @property
    def task_info(self):
        return self.__task_info

    @task_info.setter
    def task_info(self,value):
        if value is None:
            raise ValueError('value is None!')
        if not isinstance(value,Dict):
            raise ValueError('value must be a Dict!')
        self.__task_info = value

    def start(self):
        '''
        启动任务
        :return:
        '''
        try:
            db.update('update des_task set status=? where id=?',1,self.task_info.id)
            result = self.process()
            if result:
                db.update('update des_task set status=? where id=?', 2, self.task_info.id)
            else:
                db.update('update des_task set status=? where id=?',3,self.task_info.id)
        except:
            traceback.print_exc()
            log_util.error(traceback.format_exc())
            db.update('update des_task set status=? where id=?', 3, self.task_info.id)


    def stop(self):
        '''
        停止任务
        '''
        pass

    def process(self):
        pass


    @staticmethod
    def get_instance(task_info):
        if task_info.cmd != 0:
            return SingleTask(task_info)
        return CompleteFlowTask(task_info)

class SingleTask(BaseTask):
    '''
    单任务
    '''

    def process(self):
        processor = ProcessorFactory.create_instance(self.task_info)
        if processor is not None :
            return processor.do_process()
        else:
            return False




class CompleteFlowTask(BaseTask):
    '''
    全流程 任务
    '''

    def process(self):
        task_info = self.task_info
        task_info.cmd = 1
        task = SingleTask(task_info)
        result = task.process()
        if not result:
            return False

        task_info.cmd = 2
        task = SingleTask(task_info)
        result = task.process()
        if not result:
            return False

        task_info.cmd = 3
        task = SingleTask(task_info)
        result = task.process()
        if not result:
            return False
        return True

