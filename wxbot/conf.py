#!/usr/bin/env python
# coding: utf-8

import logging
from pymongo import MongoClient
import time
import sys
import json

#mysql配置
DB_HOST = "10.10.139.235"
DB_USER = "iwant"
DB_PASSWD = "iwant@201506"
DB_PORT = 3306
DB_DATABASE = "iwant"

#机器人配置
ACT_WXACCOUNT = "wellu"

#日志配置
LOG_LEVEL = logging.DEBUG
LOG_FILE = "./logs/r.log"
MSG_FILE = "./data/%s_m.log"

#附件存储
IMAGE_DIR = "./img/"

#Ucloud配置
UCLOUD_UPLOAD_SUFFIX = ".ufile.ucloud.cn"
UCLOUD_DOWNLOAD_SUFFIX = ".ufile.ucloud.com.cn"
UCLOUD_CONNECT_TIMEOUT = 30
UCLOUD_BUCKET_EXPIRES = 300
UCLOUD_LOGGER_FILEPATH = "./logs/ucloud.log"

UCLOUD_PBKEY = 'ucloudgraceful@guanjia.im14356450990001485581393' #添加自己的账户公钥
UCLOUD_PVKEY = 'ff0add32fc4123c0b34d606f6ccf751bd5a77542' #添加自己的账户私钥
UCLOUD_PBBUCKET = 'alading' #公共空间名称
UCLOUD_PVBUCKET = 'attach' #私有空间名称
UCLOUD_URL_FORMATTER = "http://%s.ufile.ucloud.com.cn/%s"    #拼完整的url

#MongoDB配置 : 存储聊天记录
#MGO_CLIENT = pymongo.Connection('10.10.139.235', 27017)
MGO_CLIENT = MongoClient('mongodb://10.10.139.235:27017/')
MGO_DB = MGO_CLIENT.iwant
MGO_WXLOG = MGO_DB.wxlog

if __name__ == '__main__':
    args = sys.argv
    if (len(args)<2):
        sys.exit()
    
    #测试MongoDB
    dtest = {
        "timestamp":int(time.time()),
        "wx_bot":"leelvgrace",
        "wx_rmk":"000008",
        "msg_type":4,
        "content":{
            "robotid":66,
            "content":{
                "from":"leelvgrace",
                "msg_type":4,
                "msgid":"test001",
                "ctype":0,
                "is_ack":1,
                "to":"000005",
                "timestamp":1472091201,
                "data":{
                    "text":"回复\"福利\"!"
                }
            },
            "cmd":"message"
        }
    }
    print json.dumps(dtest),"\n\n"
    MGO_WXLOG.insert(dtest)
    
    time.sleep(10)