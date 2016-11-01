#!/usr/bin/env python
# coding: utf-8

import logging
import logging.handlers
import random
import MySQLdb
import hashlib
import datetime
import re
import sys

from ucloud.ufile import config
from ucloud.ufile import putufile
from ucloud.ufile import uploadhitufile
from ucloud.compact import b
from ucloud.logger import set_log_file
from ucloud.ufile.config import BLOCKSIZE, get_default
from ucloud.compact import BytesIO

from wxbot import *
from common import *
from conf import *
from msg_thread import *

class MyWXBot(WXBot):
    '''
    初始化机器人
        启动机器人，登录微信之前
    '''
    def task_init(self, rid):
        self.is_task_open = 0   #业务标识(防止非业务配置手机登录)
        
        #初始化日志输出
        handler = logging.handlers.RotatingFileHandler(LOG_FILE, 
            maxBytes = 100*1024*1024, backupCount = 10)
        fmt = '[%(asctime)s - %(filename)s:%(lineno)s - %(name)s - ] %(message)s'
        formatter = logging.Formatter(fmt)   # 实例化formatter
        handler.setFormatter(formatter)      # 为handler添加formatter
        self.logger = logging.getLogger("bot")    # 获取名为tst的logger
        self.logger.addHandler(handler)           # 为logger添加handler  
        self.logger.setLevel(LOG_LEVEL)
        self.logger.info("Logger handle init success.")
        
        #初始化消息的日志输出 : 按天切分
        file_basename = MSG_FILE % get_ip_address("eth0")
        m_handler = logging.handlers.TimedRotatingFileHandler(file_basename, when='D', interval=1, 
            backupCount=0)
        m_handler.suffix = "%Y-%m-%d"
        m_formatter = logging.Formatter('[%(asctime)s - %(name)s - ] \t%(message)s')   # 实例化formatter
        m_handler.setFormatter(m_formatter)      # 为handler添加formatter
        self.msgLog = logging.getLogger("msg")
        self.msgLog.addHandler(m_handler)           # 为logger添加handler  
        self.msgLog.setLevel(logging.INFO)
        self.logger.info("MsgLogger handle init success.")
        
        #初始化Mysql连接
        ret = self.conn_db(0)
        if ret == 0:
            self.logger.info("Connect DB success.")
        else:
            return -1
        self.curr = self.conn.cursor()
        
        #构造查询队列
        self.friend_list = {}   #好友(会话)列表
        self.id2nd  = {}        #用户特征对应的好友备注
        self.last_rmk_sec = 0   #上个修改备注时间
        self.remark_update = [] #修改备注列表
        self.robot_id = rid
        self.cb_schedule = ""   #定时轮询地址
        self.cb_message = ""    #消息投递地址
        self.qreq = Queue.Queue(0)      #请求队列
        self.qresp = Queue.Queue(0)     #响应队列
        self.qack = Queue.Queue(0)      #ack队列
        
        
        #初始化ucloud
        config.set_default(uploadsuffix=UCLOUD_UPLOAD_SUFFIX, downloadsuffix=UCLOUD_DOWNLOAD_SUFFIX, 
            connection_timeout=UCLOUD_CONNECT_TIMEOUT, expires=UCLOUD_BUCKET_EXPIRES)
        set_log_file(UCLOUD_LOGGER_FILEPATH)
        self.up_handle = putufile.PutUFile(UCLOUD_PBKEY, UCLOUD_PVKEY)
        self.up_hit = uploadhitufile.UploadHitUFile(UCLOUD_PBKEY, UCLOUD_PVKEY)
        
        print "wxBot[%d] init success." % self.robot_id
        return 0
    
    #连接数据库
    def conn_db(self, flag):
        try:
            self.conn=MySQLdb.connect(host=DB_HOST,user=DB_USER,passwd=DB_PASSWD,
                db=DB_DATABASE,port=DB_PORT,charset='utf8')
        except MySQLdb.Error,e:
            self.logger.error("[1st]Mysql Connect Error %d: %s", e.args[0], e.args[1])
            return -1
        return 0
        
    #执行sql语句,返回受影响的行数
    def exe_sql(self, sql):
        self.logger.debug("execute sql[%s]", sql)
        self.curr.close()
        n = 0
        try:
            self.curr = self.conn.cursor()
            #self.curr.execute("set names utf8mb4")
            n = self.curr.execute(sql)
            self.conn.commit()
        except MySQLdb.Error,e:
            self.logger.debug("[1st]Mysql Error = %d, %s", e.args[0], e.args[1])
            #重连一次
            ret = self.conn_db(1)
            if ret != 0:
                return -1
            try:
                self.curr.close()
                self.curr = self.conn.cursor()
                #self.curr.execute("set names utf8mb4")
                n = self.curr.execute(sql)
                self.conn.commit()
            except MySQLdb.Error,e:
                self.logger.debug("[2nd]Mysql Error = %d, %s", e.args[0], e.args[1])
                return -1
        return n
    
    #构造uid
    def gen_uid(self, my, friend):
        src = "%s-%s-%s-%d" % (int(time.time()), my, friend, random.randint(10000,99999))
        m = hashlib.md5()
        m.update(src.encode('utf8'))
        uid = m.hexdigest()
        self.logger.debug("gen_uid : src = %s, uid = %s", src, uid)
        return uid
    
    #构造用户第二特征
    def gen_id2nd(self, contact):
        s = contact["Sex"]
        c = contact["City"]
        p = contact["Province"]
        sg = contact["Signature"]
        n = contact["NickName"]
        strsrc = "%d%s%s%s%s" % (s, c, p, sg, n)
        m = hashlib.md5()
        m.update(strsrc.encode('utf8'))
        return m.hexdigest()
    
    #净化用户昵称:去掉html,缩短长度
    def pure_nick_name(self, nick_name):
        #去除表情
        try:
            co = re.compile(u'[\U00010000-\U0010ffff]')
        except re.error:
            co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
        nick_name = co.sub('', nick_name)
        
        #去除html标签
        dr = re.compile(r'<[^>]+>',re.S)
        dd = dr.sub('', nick_name)
        if len(dd) > 18:
            return dd[0:18]
        return dd
    
    #更新用户备注信息
    def schd_update_remark(self):
        if len(self.remark_update) <= 0:
            return 0
        now_sec = int(time.time())
        rmk_interval = random.randint(30,60)
        if now_sec < self.last_rmk_sec + rmk_interval:
            return 0
        self.last_rmk_sec = now_sec
        wx_rmk = self.remark_update[0]["wx_rmk"]
        if True == self.update_wx_remarkname(self.remark_update[0]["account"], wx_rmk):
            self.friend_list[wx_rmk]["is_remark"] = 1
            sql = "update act_wx_friends set is_remark=1 where uid='%s'"\
                % self.friend_list[wx_rmk]["uid"]
            self.exe_sql(sql)
            del self.remark_update[0]
            self.logger.debug("Wx update remark[%s] success.", wx_rmk)
        else:
            self.logger.debug("Wx update remark[%s] failed.", wx_rmk)
        return 1
    
    '''
    定时调度：
        1)分析所有联系人
        2)监听指令,执行定时任务
    '''
    def schedule(self):
        if self.is_task_open == 0:
            return      #业务开关关闭
        self.logger.debug("in schedule")
        
        #更新用户备注信息(连续更新1条)
        if 1 == self.schd_update_remark():
            time.sleep(1)
        
    
    '''
    登录后初始化
        微信登录成功后，执行一次业务初始化
    '''
    def init_before_run(self):
        self.logger.info("---------- Do task init after wx login ----------")
        #初始化业务
        ret = self.load_task_from_db()
        if ret != 0:
            #业务初始化失败
            self.retrive_wx_uin()   #将Uin更新到机器人disp字段
            self.logger.error("----------------- Task Init failed, process exit -----------")
            sys.exit(-1)
        self.retrive_wx_uin()   #将Uin更新到机器人disp字段
        
        #初始化执行线程和队列
        wx_bot = {
            "robotid":self.robot_id,
            "wxid":self.my_account["AutoID"],
            "wx_bot":self.my_account["Wx"]
            }
        
        callback = {
            "message":self.cb_message,
            "schedule":self.cb_schedule
            }
        self.thmsg = TaskMessageThread(self.qreq, self.qresp, self.qack, 
            self.logger, self.msgLog, callback, wx_bot)
        self.thmsg.setDaemon(True)
        self.thmsg.start()   #启动线程
        
        self.logger.error("----------------- Task Init success, process running......")
        
    #更新机器人Uin
    def retrive_wx_uin(self):
        sql = "select disp from buss_activity where id=%d" % (self.robot_id)
        rn = self.exe_sql(sql)
        if rn <= 0:
            return False
        if self.my_account.has_key("AutoID"):
            wxid = self.my_account["AutoID"]
        else:
            wxid = "0"
        row = self.curr.fetchone()
        list = row[0].split(";")
        listlen = len(list)
        if listlen <= 0:
            disp = ";;;%s" % (self.my_account["Uin"])
        elif listlen == 1:
            disp = "%s;;;%s" % (list[0], self.my_account["Uin"])
        elif listlen >= 2:
            disp = "%s;%s;%s;%s" % (list[0], list[1], wxid, self.my_account["Uin"])
        sql = "update buss_activity set disp='%s' where id=%d" % (disp, self.robot_id)
        self.exe_sql(sql)
        return True
    
    #用户关系处理
    #   新增用户
    #   删除用户
    def do_proc_contact(self, contact):
        wx_bot = self.my_account["Wx"]
        wx_user = contact["Alias"]
        wx_rmk = contact["RemarkName"]
        nick_name = self.pure_nick_name(contact["NickName"])
        
        #备注记录在案
        strid2nd = self.gen_id2nd(contact)
        ugc_hit = 0
        if len(wx_rmk) > 0 and self.friend_list.has_key(wx_rmk):
            ugc_hit = 1
            #更新备注标签(上次sql执行失败/已经手动更新备注)
            if self.friend_list[wx_rmk]["is_remark"] == 0:
                sql = "update act_wx_friends set is_remark=1 where uid='%s'"\
                    % self.friend_list[wx_rmk]["uid"]
                self.exe_sql(sql)
        elif len(wx_user) >= 1:#微信号存在
            for key, value in self.friend_list.items():
                if value["wx_user"] == wx_user:
                    wx_rmk = key
                    ugc_hit = 2
                    break
        else:
            if self.id2nd.has_key(strid2nd):
                wx_rmk = self.id2nd[strid2nd]
                ugc_hit = 3
        if ugc_hit > 0:
            self.account_info["normal_member"][contact["UserName"]]["RemarkName"] = wx_rmk
            if ugc_hit > 1:
                #重新更新用户备注信息
                self.remark_update.append({"account":contact, "wx_rmk":wx_rmk})
            #更新friend_list信息
            self.friend_list[wx_rmk]["info"]["UserName"] = contact["UserName"]
            self.friend_list[wx_rmk]["info"]["NickName"] = contact["NickName"]
            self.friend_list[wx_rmk]["info"]["Sex"] = contact["Sex"]
            self.friend_list[wx_rmk]["info"]["Signature"] = contact["Signature"]
            self.friend_list[wx_rmk]["info"]["City"] = contact["City"]
            self.friend_list[wx_rmk]["info"]["Province"] = contact["Province"]
            if strid2nd != self.friend_list[wx_rmk]["info"]["id2nd"]:
                #用户信息变更
                self.friend_list[wx_rmk]["info"]["id2nd"] = strid2nd
                strinfo = MySQLdb.escape_string(json.dumps(self.friend_list[wx_rmk]["info"]))
                self.logger.debug("Update User Info for wx_rmk[%s] : from[%s] to [%s]",
                    wx_rmk, self.friend_list[wx_rmk]["info"]["id2nd"], strid2nd)
                sql = "update act_wx_friends set "\
                        "nick_name='%s',"\
                        "info='%s' "\
                        "where uid='%s'"\
                        % (nick_name, strinfo, self.friend_list[wx_rmk]["uid"])
                self.exe_sql(sql)
            
            self.logger.debug("Account : \n\t%s", json.dumps(self.friend_list[wx_rmk]))
            return 0
        
        #用户不存在, 插入该用户
        t_now = int(time.time()) % 86400
        wx_rmk = "%04d%05d%02d" % (len(self.friend_list), t_now, int(random.randint(0, 99)))
        id2nd = self.gen_id2nd(contact)
        contact["id2nd"] = id2nd
        fn = self.get_head_img(contact["UserName"]) #获取用户头像
        small_key = "wx_headimg_%s_%s" % (wx_bot, wx_rmk)
        ret, resp = self.up_handle.putfile(UCLOUD_PBBUCKET, small_key, fn)
        if resp.status_code != 200:
            self.logger.debug("putfile[%s] failed, what = %d:%s", 
                fn, resp.status_code, resp.content)
            contact["head_imgurl"] = ""
        else:
            contact["head_imgurl"] = UCLOUD_URL_FORMATTER % (UCLOUD_PBBUCKET, small_key)
        info = MySQLdb.escape_string(json.dumps(contact))
        iter = 0
        while iter < 3:
            uid = self.gen_uid(wx_bot, wx_rmk)
            strnow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sql = "insert into act_wx_friends"\
                " (wx_bot,wx_rmk,wx_user,nick_name,uid,info,status,create_time)"\
                " values ('%s','%s','%s','%s','%s','%s',1,'%s')"\
                % (wx_bot,wx_rmk,wx_user,nick_name,uid,info,strnow)
            rn = self.exe_sql(sql)
            if rn == 1:
                break
            iter += 1
        if iter < 3:
            #更新friendlist
            self.friend_list[wx_rmk] = {
                "wx_user":wx_user,
                "uid":uid,
                "nick_name":nick_name,
                "push_flag":0,
                "view_count":0,
                "is_remark":0,
                "info":contact,
                "status":1,
                "msg_send":0     #发送消息条数
                }
            #加载第二特征
            self.id2nd[contact["id2nd"]] = wx_rmk
            self.logger.debug("add friend[%s] , info = [%s]", wx_rmk, json.dumps(self.friend_list[wx_rmk]))
            #插入成功了,通知业务侧
            new_msg = {
                "robotid":self.robot_id,
                "wxid":self.my_account["AutoID"],
                "cmd":"friend_add",
                "content":{
                    "sex":contact["Sex"],
                    "province":contact["Province"],
                    "city":contact["City"],
                    "remark_name":wx_rmk,
                    "alias":wx_user,
                    "signature":contact["Signature"],
                    "nick_name":nick_name,
                    "headimg":contact["head_imgurl"]
                }
            }
            self.qreq.put(json.dumps(new_msg))  #压队列(通知业务,等待响应)
            self.logger.debug("Account : \n\t%s", json.dumps(self.friend_list[wx_rmk]))
            #等待更新用户备注信息
            self.remark_update.append({"account":contact, "wx_rmk":wx_rmk})
        else:
            #插入用户失败：系统错误(告知用户,删除好友后再次加好友)
            self.logger.error("ADD FRIEND FAILED.")
            #self.send_msg_by_uid(u"很抱歉，系统错误，请您删除后再次添加好友，谢谢！", contact["UserName"])
        #end to else
        return 0
    
    #处理群信息
    def do_proc_group(self, gp):
        self.logger.debug("Group : \n\t%s", json.dumps(gp))
        #TODO : 群处理方案未定
        return 0
    
    
    #加载数据中的业务数据
    #   self.friends = {}
    def load_task_from_db(self):
        flag = 0
        #判断当前登录的微信号是否为活动机器人
        sql = "select id,content,weight from buss_activity where status=1 and classify='%s'" % ACT_WXACCOUNT
        if self.exe_sql(sql) == -1:
            return -1   #业务加载失败 ：主动退出
        res = self.curr.fetchall()
        for r in res:
            id = r[0]
            jcont = json.loads(r[1])
            if jcont["uin"] == self.my_account["Uin"]:
                if jcont.has_key('wx') and jcont.has_key('msg_cb') and jcont.has_key('sync_cb'):
                    self.my_account["Wx"] = jcont["wx"] #存储本机器人微信号
                    self.my_account["AutoID"] = id      #存储机器人的ID
                    self.cb_schedule = jcont["sync_cb"] #定时轮询地址
                    self.cb_message = jcont["msg_cb"]   #消息投递地址
                    flag = 1
                    break
        if flag == 1:
            self.is_task_open = 1
            self.logger.info("task account success, my = \n\t%s", json.dumps(self.my_account))
            #将绑定关系映射到机器人中
            sql = "update buss_activity set weight=%d where id=%s"\
                % (self.my_account["AutoID"], self.robot_id)
            if self.exe_sql(sql) == -1:
                self.logger.error("Bind Wx[%d] to Robot[%d] failed.", self.my_account["AutoID"],
                    self.robot_id)
                return -1
        else:
            self.is_task_open = 0
            self.logger.error("task account failed, my = \n\t%s", json.dumps(self.my_account))
            return -1
        wx_bot = self.my_account["Wx"]
        #加载遍历好友列表
        sql = "select uid,wx_user,nick_name,push_flag,wx_rmk,is_remark,info,status from act_wx_friends"\
              " where wx_bot='%s'" % wx_bot
        if self.exe_sql(sql) == -1:
            return -1
        res = self.curr.fetchall()
        for r in res:
            info = json.loads(r[6])
            self.friend_list[r[4]] = {
                "wx_user":r[1],
                "uid":r[0],
                "nick_name":r[2],
                "push_flag":r[3],
                "view_count":0,
                "is_remark":int(r[5]),
                "info":info,
                "status":int(r[7]),
                "msg_send":0             #发送消息条数
            }
            
            if self.friend_list[r[4]]["status"] == 0:
                #离线的时候重新加回好友呢？
                self.friend_list[r[4]]["status"] = 2
            
            #加载第二特征
            if info.has_key("id2nd"):
                self.id2nd[info["id2nd"]] = r[4]
            
        #对比会话列表(联系人)
        for account in self.contact_list:
            self.do_proc_contact(account)
        
        #对比群列表
        for gp in self.group_list:
            self.do_proc_group(gp)
        
        self.logger.info("Init task success, base_url = %s", self.base_uri)
        
        return 0
    
    
    '''
    处理新增微信好友
        好友变更提示
    '''
    def handle_contact_new(self, contact, citer):
        self.logger.debug("-------- we got new friend : --------")
        #业务并没有开启
        if self.is_task_open == 0:
            return -1
        
        #新增联系人
        bret = self.verify_user(contact, u"终于等到你！")
        if bret:
            self.logger.debug("verify_user : success.")
        else:
            self.logger.debug("verify_user : failed.")
        
        #将该用户入库
        self.do_proc_contact(contact)
        
        return 0
    
    '''
    处理新增微信群
        群变更提示
    '''
    def handle_group_new(self, contact, citer):
        self.logger.debug("-------- we got new group : --------")
        #将该群入库
        self.do_proc_group(contact);
        return 0
        
    
    '''
    处理所有的微信消息
    '''
    def handle_msg_all(self, msg, org_msg):
        data_string = json.dumps(msg)
        msgtype = msg['msg_type_id']
        #---------- 不进入业务处理部分 -------
        #只作为回声虫
        if self.is_task_open == 0:
            if msgtype == 4 and msg['content']['type'] == 0:
                #收到文本消息
                sstr = "Echo : %s" % (msg['content']['data'])
                self.send_msg_by_uid(sstr, msg['user']['id'])
            return
        
        #----------- 业务处理部分 -------------
        '''
            V1.0只处理联系人消息 和 群消息
        '''
        if msgtype != 1 and msgtype != 3 and msgtype != 4:
            self.logger.debug('no need to process : %d', msgtype)
            return
        
        self.logger.debug('receive new msg : type = %d ------ ', msgtype)
        self.logger.debug(data_string)
        #提取消息元素
        wx_bot = self.my_account["Wx"]
        new_msg = {
            "robotid":self.robot_id,
            "wxid":self.my_account["AutoID"],
            "cmd":"message",
            "content":{
                "from":"",
                "to":"",
                "timestamp":int(time.time()),
                "msg_type":msgtype,
                "ctype":msg['content']['type']
            }
        }
        #------------------------------------------------
        #消息源
        if msgtype == 1:#自己发送的消息
            new_msg["content"]["from"] = wx_bot
            user_id = msg['to_user_id']
            #TODO : 处理自己发的群消息
            if self.account_info["normal_member"].has_key(user_id) and \
                self.account_info["normal_member"][user_id].has_key("RemarkName"):
                new_msg["content"]["to"] = self.account_info["normal_member"][user_id]["RemarkName"]
            else:
                #未知消息接收人
                self.logger.error("unknown msg receiver, as following : \n%s", data_string)
                return
        elif msgtype == 4:#联系人发来的消息
            new_msg["content"]["to"] = wx_bot
            user_id = msg['user']['id']
            if self.account_info["normal_member"].has_key(user_id) and \
                self.account_info["normal_member"][user_id].has_key("RemarkName"):
                new_msg["content"]["from"] = self.account_info["normal_member"][user_id]["RemarkName"]
            else:
                #未知消息发送人
                self.logger.error("unknown msg sender, as following : \n%s", data_string)
                return
        elif msgtype == 3:#群消息
            self.logger.debug("group message ......")
            new_msg["content"]["from"] = msg['user']['name']
            new_msg["content"]["to"] = wx_bot
            if msg['content'].has_key("user"):
                new_msg["content"]["guser"] = msg['content']['user']['name']    #群用户名
            else:
                new_msg["content"]["guser"] = msg['user']['id'] #默认填写群ID
            
        #------------------------------------------------
        #识别消息内容本身
        if msg['content']['type'] == 0:
            #文本消息
            new_msg["content"]["data"] = {
                "text":msg['content']['data']
                }
        elif msg['content']['type'] == 7:
            #分享类型消息
            new_msg["content"]["data"] = msg['content']['data']
        elif msg['content']['type'] == 3:
            #图片消息
            bcont = msg['content']['img'].decode('hex')
            m = hashlib.md5()
            m.update(bcont)
            md5str = m.hexdigest()
            fileext = "jpg"
            if msg['content']['content-type'] == "image/png":
                fileext = "png"
            elif msg['content']['content-type'] == "image/tiff":
                fileext = "tiff"
            elif msg['content']['content-type'] == "image/gif":
                fileext = "gif"
            filepath = "%s%s.%s" % (IMAGE_DIR, md5str, fileext)
            if not os.path.exists(filepath):
                file = open(filepath, "wb")
                file.write(bcont)
                file.flush()
                file.close()
            
            #附件上传到ucloud
            ret, resp = self.up_hit.uploadhit(UCLOUD_PBBUCKET, md5str, filepath)
            if resp.status_code == 200:
                #文件已经存在
                self.logger.debug("file[%s] existed.", filepath)
            else:
                #文件不存在(总之就是要再传一次)
                self.logger.debug("file[%s] not existed.", filepath)
                ret, resp = self.up_handle.putfile(UCLOUD_PBBUCKET, md5str, filepath)
                if resp.status_code != 200:
                    self.logger.debug("putfile[%s] failed, what = %d:%s", 
                        filepath, resp.status_code, resp.error)
            url = UCLOUD_URL_FORMATTER % (UCLOUD_PBBUCKET, md5str)
            #组装消息
            new_msg["content"]["data"] = {
                "url":url,
                "ctype":msg['content']['content-type'],
                "md5":md5str
                }
        elif msg['content']['type'] == 4:
            #语音消息
            bcont = msg['content']['voice'].decode('hex')
            m = hashlib.md5()
            m.update(bcont)
            md5str = m.hexdigest()
            fileext = "mp3"
            if msg['content']['content-type'] == "audio/amr":
                fileext = "amr"
            elif msg['content']['content-type'] == "audio/wav":
                fileext = "wav"
            filepath = "%s%s.%s" % (IMAGE_DIR, md5str, fileext)
            if not os.path.exists(filepath):
                file = open(filepath, "wb")
                file.write(bcont)
                file.flush()
                file.close()
            #附件上传到ucloud
            ret, resp = self.up_hit.uploadhit(UCLOUD_PBBUCKET, md5str, filepath)
            if resp.status_code == 200:
                #文件已经存在
                self.logger.debug("file[%s] existed.", filepath)
            else:
                #文件不存在(总之就是要再传一次)
                self.logger.debug("file[%s] not existed.", filepath)
                ret, resp = self.up_handle.putfile(UCLOUD_PBBUCKET, md5str, filepath)
                if resp.status_code != 200:
                    self.logger.debug("putfile[%s] failed, what = %d:%s", 
                        filepath, resp.status_code, resp.content)
            url = UCLOUD_URL_FORMATTER % (UCLOUD_PBBUCKET, md5str)
            #组装消息
            new_msg["content"]["data"] = {
                "url":url,
                "ctype":msg['content']['content-type'],
                "md5":md5str
                }
        elif msg['content']['type'] == 1:
            #地理位置
            title = msg['content']['data']
            pos = title.find(":")   #描述用“:”隔开
            if pos > 0:
                title = title[0:pos]
            new_msg["content"]["data"] = {
                "title":title,
                "url":msg['content']['url']
                }
        elif msg['content']['type'] == 5:
            #名片
            new_msg["content"]["data"] = msg['content']['data']
        elif msg['content']['type'] == 6:
            #动画
            new_msg["content"]["data"] = msg['content']['data']
        elif msg['content']['type'] == 8:
            #视频
            new_msg["content"]["data"] = msg['content']['data']
        elif msg['content']['type'] == 12:
            #TODO : 系统提示
            text = msg['content']['data']
            schema = u"发送朋友验证"
            npos = text.find(schema)
            if npos >= 0:
                if not self.account_info['normal_member'][msg['user']['id']].has_key('RemarkName'):
                    return
                wx_rmk = self.account_info['normal_member'][msg['user']['id']]['RemarkName']
                if not self.friend_list.has_key(wx_rmk):
                    return
                if self.friend_list[wx_rmk]["status"] == 0:
                    return
                self.logger.info("User[%s] delete [%s] from his/her friend list.", wx_rmk, wx_bot)
                uid = self.friend_list[wx_rmk]["uid"]
                sql = "update act_wx_friends set status=0 where uid='%s'" % (uid)
                self.exe_sql(sql)
                self.friend_list[wx_rmk]["status"] = 0
                #TODO : 好友移除: 通知业务
                new_msg = {
                    "robotid":self.robot_id,
                    "wxid":self.my_account["AutoID"],
                    "cmd":"friend_del",
                    "content":{
                        "sex":self.friend_list[wx_rmk]["info"]["Sex"],
                        "province":self.friend_list[wx_rmk]["info"]["Province"],
                        "city":self.friend_list[wx_rmk]["info"]["City"],
                        "remark_name":wx_rmk,
                        "alias":self.friend_list[wx_rmk]["info"]["Alias"],
                        "signature":self.friend_list[wx_rmk]["info"]["Signature"],
                        "nick_name":self.friend_list[wx_rmk]["info"]["NickName"],
                        "headimg":self.friend_list[wx_rmk]["info"]["head_imgurl"]
                    }
                }
            else:
                return
        else:
            #其他消息一律不处理
            return
        
        #压队列(通知业务,等待响应)
        self.qreq.put(json.dumps(new_msg))
        
        return
    
#----------------------------------------------------
"""
    响应线程
        处理所有业务侧对用户的发包请求
        
"""
class MsgResponseThread(threading.Thread):
    '''
        @param myrobot MyWXBot 对象
    '''
    def __init__(self, myrobot):
        threading.Thread.__init__(self)
        self.psvr = myrobot #父对象
        self.msg_list = Queue.Queue(0)      #消息发送队列
        
        self.msgctrl = {}       #消息拥塞控制:基于单个用户(每个用户1/秒)
    
    '''
        主运行体
    '''
    def run(self):
        while True:
            if self.psvr.is_task_open == 0: #等待业务启动
                time.sleep(3)
                continue
            
            #循环发送消息
            self.cycle_send_msg()
            
            #获取响应
            try:
                strmsg = self.psvr.qresp.get(True, 1)
                self.psvr.logger.debug("Response thread running...")
                bret = self.do_proc_msg(json.loads(strmsg))
            except Exception as e:
                continue
            
            
    
    #处理来自业务的消息
    def do_proc_msg(self, msg):
        self.psvr.logger.debug("Response message as following : \n\t%s", json.dumps(msg))
        if msg["cmd"] == "cmd":
            #TODO : >>>>>> 暂时忽略该类型消息
            self.psvr.logger.debug("ignore type[%s] response.", msg["cmd"])
            return
        elif msg["cmd"] != "msg":
            #未知消息类型
            self.psvr.logger.error("unsupported type[%s] response.", msg["cmd"])
            return
        #处理消息类型
        for item in msg["content"]:
            #消息进入发送队列
            if not item.has_key("to"):
                #群发所有联系人
                for wx_rmk,info in self.psvr.friend_list.items():
                    item["to"] = wx_rmk
                    strmsg = json.dumps(item)
                    self.msg_list.put(strmsg)
                    self.psvr.logger.debug("Add Message[%d] to wx_rmk[%s], what = %s", 
                        self.msg_list.qsize(), wx_rmk, strmsg)
            else:
                #单发给某个人
                self.msg_list.put(json.dumps(item))
        
        
    '''
        循环发送消息,控制发送速度
    '''
    def cycle_send_msg(self):
        #暂时不控制
        qlen = self.msg_list.qsize() #消息队列的长度
        qiter = 0
        while True:
            if self.msg_list.qsize() <= 0:
                return
            item = json.loads(self.msg_list.get())
            wx_rmk = item["to"]
            qiter += 1
            
            '''
            #判断该用户的发送间隔
            now_sec = int(time.time())
            if self.msgctrl.has_key(wx_rmk) and self.msgctrl[wx_rmk]+1 > now_sec:
                #发送间隔还没到:加到队尾
                #self.psvr.logger.debug("TO wx_rmk[%s] : delay this msg.", wx_rmk)
                self.msg_list.put(json.dumps(item))
                if qiter >= qlen:
                    self.psvr.logger.debug("Travel all : qlen[%d] == qiter[%d]", qlen, qiter)
                    time.sleep(0.2) #所有人都没到发送间隔
                    qlen = self.msg_list.qsize()
                    qiter = 0
                continue
            else:
                self.msgctrl[wx_rmk] = now_sec
            self.psvr.logger.debug("Msglist[%d] ===> to wx_rmk[%s], what : %s", 
                self.msg_list.qsize(), wx_rmk, json.dumps(item))
            '''
            
            #消息发送
            is_ack = 0
            if item.has_key("is_ack") and item.has_key("msgid") and item["is_ack"] != 0:
                is_ack = 1  #需要回执
            sendflag = 0    #发送标志
            while True:#循环控制,代码可读性
                if not self.psvr.friend_list.has_key(wx_rmk):
                    self.psvr.logger.error("unknown user wx_rmk[%s]", wx_rmk)
                    break
                if self.psvr.friend_list[wx_rmk]["status"] == 0:
                    #好友已经被删除
                    self.psvr.logger.error("WxRmk[%s] has removed friend from it's list.", wx_rmk)
                    break
                if not item.has_key("msg_type") or not item.has_key("ctype") or not item.has_key("data"):
                    self.psvr.logger.error("unknown msg as following : %s", json.dumps(item))
                    break
                if item["msg_type"] != 4:
                    self.psvr.logger.error("unsupported msg_type[%d]", item["msg_type"])
                    break
                to_user_id = self.psvr.friend_list[wx_rmk]["info"]["UserName"]
                if item["ctype"] == 0:      #文本消息
                    if not item["data"].has_key("text"):
                        break
                    self.psvr.logger.debug("send text[%s] to [%s]", item["data"]["text"], to_user_id)
                    bret = self.psvr.send_msg_by_uid(item["data"]["text"], to_user_id)
                    if bret == True:
                        sendflag = 1
                    #发送文本,等待1秒
                    time.sleep(0.5)
                elif item["ctype"] == 3:    #图片消息
                    if not item["data"].has_key("url") and not item["data"].has_key("md5"):
                        break
                    filepath = "%s%s.jpg" % (IMAGE_DIR, item["data"]["md5"])
                    if not os.path.exists(filepath):
                        filepath = DownloadImage2Local(item["data"]["url"], IMAGE_DIR)
                        if filepath == "":
                            break
                    self.psvr.logger.debug("send image[%s] to [%s]", filepath, to_user_id)
                    bret = self.psvr.send_img_msg_by_uid(filepath, to_user_id)
                    if bret == True:
                        sendflag = 1
                    else:
                        self.psvr.logger.debug("send image[%s] to [%s] failed.", filepath, to_user_id)
                    #发送图片,等待2秒
                    time.sleep(1)
                else:
                    self.psvr.logger.error("unsupported msg_content_type[%d]", item["ctype"])
                    break
                break
            #end of while control
            if is_ack == 1: #添加回执
                strmsg = json.dumps({"msgid":item["msgid"],"to":wx_rmk,"ack":sendflag})
                self.psvr.qack.put(strmsg)
            
            #消息日志
            item["timestamp"] = int(time.time())
            item["from"] = self.psvr.my_account["Wx"]
            logmsg = {
                "cmd":"message",
                "robotid":self.psvr.robot_id,
                "content":item
                }
            LoggingMessage(self.psvr.msgLog, logmsg, sendflag, self.psvr.my_account["Wx"])
            
            #更新用户状态
            if sendflag == 1 :
                if self.psvr.friend_list[wx_rmk]["msg_send"] >= 1:
                    if self.psvr.friend_list[wx_rmk]["status"] == 2:
                        #失联用户召回
                        sql = "update act_wx_friends set status=1 where uid='%s'"\
                            % self.psvr.friend_list[wx_rmk]["uid"]
                        self.psvr.exe_sql(sql)
                self.psvr.friend_list[wx_rmk]["msg_send"] += 1
            
            
#----------------------------------------------------
#----------------------------------------------------
#----------------------------------------------------
#main function

def main():
    args = sys.argv
    if (len(args)<2):
        sys.exit()
    rid = args[1] #获得机器人启动的ID
    #初始化机器人 ------
    bot = MyWXBot()
    ret = bot.task_init(int(rid))
    if ret != 0:
        #机器人初始化失败
        print "robot init failed."
        return -1
    bot.conf['qr'] = 'png'      #二维码图片
    
    #初始化响应线程 ------
    thresp = MsgResponseThread(bot)
    thresp.setDaemon(True)  #随主线程一起退出
    thresp.start()
    
    #运行机器人 ------
    bot.run()


if __name__ == '__main__':
    main()
