#!/usr/bin/env python
# coding: utf-8

"""
    消息线程
        主线程消息回调业务方
        回收从业务方返回的指令
"""
import Queue
import threading
import time
import random
import logging
import requests
import json
import traceback
from traceback import format_exc
from requests.exceptions import ConnectionError, ReadTimeout

from common import *

MSGTHREAD_SCHEDULE_INTERVAL = 30    #定时轮询间隔

class TaskMessageThread(threading.Thread):
    '''
        @param qin 消息队列
        @param qout 响应队列
        @param qack 回执队列,存储主线程发送消息的回执
        @param logger 日志句柄
        @param mlogger 消息本地化存储
        @param callback {"message":"xxxxx", "schedule":"xxxxx"}
        @param wx_bot 机器人微信帐号,格式如下
            {
                "robotid":100,
                "wxid":19,
                "wx_bot":"wellmi001"
            }
    '''
    def __init__(self, qin, qout, qack, logger, mlogger, callback, wx_bot):
        threading.Thread.__init__(self)
        self.logger = logger
        self.mlogger = mlogger
        self.qin = qin
        self.qout = qout
        self.qack = qack
        self.cb_message = callback["message"]
        self.cb_shcedule = callback["schedule"]
        self.wx_bot = wx_bot
        self.ack_list = []  #记录应答表
        self.last_schedule_sec = int(time.time())
        self.seq_number = 0
    
    '''
        主运行体
    '''
    def run(self):
        while True:
            if self.qin.qsize() > 0:
                msg = json.loads(self.qin.get())
                bret = self.do_proc_msg(msg)
                #消息记录到日志并入库
                if bret == True:
                    LoggingMessage(self.mlogger, msg, 1, self.wx_bot["wx_bot"])
                else:
                    LoggingMessage(self.mlogger, msg, 0, self.wx_bot["wx_bot"])
            else:
                self.do_proc_schedule()
            time.sleep(0.2)
    
    #处理接收到的消息
    def do_proc_msg(self, msg):
        #组装消息
        try:
            data = {
                "robotid":msg["robotid"],
                "wxid":msg["wxid"],
                "cmd":msg["cmd"],
                "content":[],
                "seq_number":self.seq_number
                }
            self.seq_number += 1
            data["content"].append(msg["content"])
            headers = {'Content-Type': 'application/json; charset=UTF-8'}
            #输出组装的消息内容
            self.logger.debug("new_message as following : \n%s", json.dumps(data))
            
            r = requests.post(self.cb_message, timeout=30, data=json.dumps(data), headers=headers)
            self.logger.debug("Response content = %s", r.text)
            dic = r.json()
            if dic["error"] != 0:
                self.logger.error("Bad response, what retcode = %d, msg = %s", 
                    dct["error"], dic["content"])
                return False
            self.qout.put(json.dumps(dic["content"]))   #正确的响应才会送到机器人返回
        except Exception as e:
            self.logger.error("POST Message failed.")
            return False
        return True
        
    
    #处理定时轮询
    def do_proc_schedule(self):
        now_sec = int(time.time())
        if now_sec - self.last_schedule_sec < MSGTHREAD_SCHEDULE_INTERVAL:
            return True
        self.last_schedule_sec = now_sec
        
        ack = []
        iter = 0
        while iter < 10:
            iter += 1
            if self.qack.qsize() > 0:
                strack = self.qack.get()
                ack.append(json.loads(strack))
            else:
                break
        jreq = {
            "cmd":"sync",
            "seq_number":self.seq_number,
            "robotid":self.wx_bot["robotid"],
            "wxid":self.wx_bot["wxid"],
            "content":{
                "ack":ack
                }
            }
        self.seq_number += 1
        #发送请求
        try:
            headers = {'Content-Type': 'application/json; charset=UTF-8'}
            r = requests.post(self.cb_shcedule, timeout=30, data=json.dumps(jreq), headers=headers)
            self.logger.debug("Response content = %s", r.text)
            dic = r.json()
            if dic["error"] != 0:
                self.logger.error("Bad response, what retcode = %d, msg = %s", 
                    dct["error"], dic["content"])
                return False
            self.qout.put(json.dumps(dic["content"]))   #正确的响应才会送到机器人返回
        except Exception as e:
            #记录错误的消息日志
            self.logger.error("POST Schedule failed, what = %s, trace = %s", 
                e.message, traceback.format_exc())
            return False
        
        return True
    
    
if __name__ == '__main__':
    args = sys.argv
    if (len(args)<2):
        sys.exit()
    
    