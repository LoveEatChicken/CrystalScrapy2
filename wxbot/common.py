#!/usr/bin/env python
# coding: utf-8

import os
import sys
import random
import httplib
import base64
import json
import time
import hashlib
from urlparse import urlparse
import logging
from conf import MGO_WXLOG
import socket
import fcntl
import struct
#----------------------------------------------------
'''
    deprecated : 新浪的服务参数不对,没有调试通过
    新浪的短网址服务 
        @param url 需要截短的长网址
        
        @return 短网址,出错正则返回 "" （空字符串）
'''
def ShortLinkBySina(url):
    short_base_url = "http://dwz.wailian.work/api.php?site=sina&url="
    req_url = "%s%s" % (short_base_url, base64.urlsafe_b64encode(url))
    try:
        httpClient = httplib.HTTPConnection('dwz.wailian.work', 80, timeout=30)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36"
                    , "Accept": "application/json"
                    , "Referer": "http://dwz.wailian.work/"}
        httpClient.request('GET', req_url, None, headers)
        print "req_url = ", req_url
        #response是HTTPResponse对象
        response = httpClient.getresponse()
        if response.status != 200 or response.reason != "OK":
            return ""
        jcont = json.loads(response.read())
        if jcont.has_key("result") == False or jcont.has_key("data") == False:
            return ""
        if jcont["result"].lower() != "ok":
            return ""
        if jcont["data"].has_key("short_url") == False:
            return ""
        return jcont["data"]["short_url"]
    except Exception, e:
        return ""
    finally:
        if httpClient:
            httpClient.close()
    return ""


#----------------------------------------------------
'''
    微信公众平台的短网址服务 
        微信短网址服务需要依托于一个公众平台
        @param token 访问token
        @param url 需要截短的长网址
        
        @return 短网址,出错正则返回 "" （空字符串）
'''
def ShortLinkByWx(token, url):
    short_base_url = "https://api.weixin.qq.com/cgi-bin/shorturl?access_token="
    req_url = "%s%s" % (short_base_url, token)
    try:
        httpClient = httplib.HTTPConnection('api.weixin.qq.com', 80, timeout=30)
        headers = {"Content-Type":"application/json"}
        params = {
            "action":"long2short",
            "long_url":url
        }
        httpClient.request('POST', req_url, json.dumps(params), headers)
        #print "req_url = ", req_url
        #response是HTTPResponse对象
        response = httpClient.getresponse()
        if response.status != 200 or response.reason.lower() != "ok":
            return ""
        content = response.read()
        jcont = json.loads(content)
        if jcont.has_key("errcode") == False or jcont.has_key("errmsg") == False:
            return ""
        if jcont["errcode"] != 0:
            return ""
        if jcont.has_key("short_url") == False:
            return ""
        return jcont["short_url"]
    except Exception, e:
        #print e
        return ""
    finally:
        if httpClient:
            httpClient.close()
    return ""
#----------------------------------------------------
'''
    下载图片内容到本地目录 
        @param url 图片地址
        @param dir 本地目录
        
        @return 访问文件名称(全路径),""表示下载出错s
'''
def DownloadImage2Local(url, dir):
    purl = urlparse(url)    #解析url
    global httpClient
    try:
        httpClient = httplib.HTTPConnection(purl.hostname, purl.port, timeout=30)
        httpClient.request('GET', url)
        #response是HTTPResponse对象
        response = httpClient.getresponse()
        if response.status != 200 or response.reason.lower() != "ok":
            return ""
        content_type = response.getheader("content-type").lower()
        content = response.read()
        m = hashlib.md5()
        m.update(content)
        if not os.path.exists(dir):
            os.makedirs(dir)
        if(not dir.endswith("/")):
            filepath = "%s/%s.jpg" % (dir, m.hexdigest())
        else:
            filepath = "%s%s.jpg" % (dir, m.hexdigest())
        if not os.path.exists(filepath):
            file = open(filepath, "wb")
            file.write(content)
            file.flush()
            file.close()
        return filepath
    except Exception, e:
        #print e
        return ""
    finally:
        if httpClient:
            httpClient.close()
    return ""

#----------------------------------------------------
'''
    将消息记录到本地日志 & 入库
        @param lhandle 日志句柄
        @param jmsg 消息体(dict)
        @param flag 发送标志 0=失败；1=成功
        @param wx_bot 机器人微信帐号
        @param robotid 机器人配置ID
        
        @return None
'''
def LoggingMessage(lhandle, jmsg, flag, wx_bot):
    if jmsg["cmd"] != "message":
        return
    robotid = jmsg["robotid"]
    now_sec = jmsg["content"]["timestamp"]
    wx_rmk = jmsg["content"]["to"]
    if jmsg["content"]["to"] == wx_bot:
        wx_rmk = jmsg["content"]["from"]
    lhandle.info("%s\t%d\t%s\t%s\t%s\t%s", now_sec,
        flag,
        wx_bot,
        wx_rmk,
        jmsg["content"]["ctype"],
        json.dumps(jmsg)
    )
    #成功的消息插入到MongoDB：iwant.wxlog
    if flag == 0:
        return
    dlog = {
        "timestamp":int(time.time()),
        "wx_bot":wx_bot,
        "wx_rmk":wx_rmk,
        "content":json.dumps(jmsg)
        }
    MGO_WXLOG.insert(dlog)
    return
#----------------------------------------------------
'''
    获取网口对应的IP(V4)地址
'''
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]) )[20:24])

#----------------------------------------------------
#----------------------------------------------------



if __name__ == '__main__':
    dict = {"a":1,"b":2,"c":3,"d":4}
    print "len = %d" % len(dict)
    
    str = u"中a国好ren"
    print "cat : %s" % str[0:3]
    
    print "inner ip address = %s" % get_ip_address("eth0")
    
    args = sys.argv
    if (len(args)<2):
        sys.exit()
    print "test for common"
    token = args[1]
    #print "ShortLinkByWx : \n", ShortLinkByWx(token, "https://neutie.com/page/wx/stayup/shows.html")
    print "DownloadImage2Local : \n"
    filename = DownloadImage2Local(args[1], "./")
    print "filename : ",filename,"\n"
    