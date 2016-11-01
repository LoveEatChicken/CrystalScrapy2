#!/usr/bin/env python
# encoding=utf-8
""""
bin/main.py
"""

import os
import os.path
import sys
reload(sys)
# sys.setdefaultencoding("utf-8")
sys.path.append("../pythonlib")
sys.path.append("./pythonlib")
import argparse
import ConfigParser
import logging
import logging.config
import subprocess
import json
import tarfile
import hashlib
import time
import shutil
import datetime
import socket

import mail


class JsonStatus(object):

    """
    JsonStatus
    """

    def __init__(self):
        self.obj = dict()

    def put(self, k, v):
        self.obj[k] = v

    def get(self, k):
        if k in self.obj:
            return self.obj[k]
        return None

    def fromFile(self, fileFullPath):
        infh = None
        logging.info("load file [%s]", fileFullPath)
        try:
            infh = open(fileFullPath, "r")
            if infh is None:
                logging.warning("open file[%s] fail", fileFullPath)
                return -1
            filecont = infh.read()

            self.obj = json.loads(filecont)
            if self.obj is None:
                logging.warning("parse file content[%s] as json fail",
                                self.obj)
                return -2
            return 0
        except Exception as e:
            logging.warning("got exception [%s]", str(e))
            return -3
        finally:
            if infh is not None:
                infh.close()

    def toFile(self, fileFullPath):
        outfh = None
        try:
            outfh = open(fileFullPath, "w+")
            if outfh is None:
                logging.warning("open file [%s] fail", fileFullPath)
                return -1
            json.dump(self.obj, outfh)
            return 0
        except Exception as e:
            logging.warning("got exception [%s]", str(e))
            return -1
        finally:
            if outfh is not None:
                outfh.close()


class UpdateStatus(JsonStatus):

    """
    UpdateStatus
    """

    def __init__(self):
        super(UpdateStatus, self).__init__()

        self.lastUpdateTime = 0
        self.lastUpdateTimeStr = ""

    def fromFile(self, fileFullPath):
        ret = super(UpdateStatus, self).fromFile(fileFullPath)
        if ret != 0:
            return ret

        self.lastUpdateTime = 0
        self.lastUpdateTimeStr = ""

        tmp = self.get("lastUpdateTime")
        if tmp is not None:
            self.lastUpdateTime = tmp

        self.lastUpdateTimeStr = time.strftime(
            "%Y%m%d:%H%M%S", time.localtime(self.lastUpdateTime))
        logging.info("load status : lastUpdateTime timestamp[%f]",
                     self.lastUpdateTime)
        logging.info("load status : lastUpdateTime strftime[%s]",
                     self.lastUpdateTimeStr)

    def toFile(self, fileFullPath):
        self.lastUpdateTimeStr = time.strftime(
            "%Y%m%d:%H%M%S", time.localtime(self.lastUpdateTime))

        self.put("lastUpdateTime", self.lastUpdateTime)
        self.put("lastUpdateTimeStr", self.lastUpdateTimeStr)
        logging.info("save status : lastUpdateTime timestamp[%f]",
                     self.lastUpdateTime)
        logging.info("save status : lastUpdateTime strftime[%s]",
                     self.lastUpdateTimeStr)
        super(UpdateStatus, self).toFile(fileFullPath)


class RemoteStatus(JsonStatus):

    def __init__(self):
        super(RemoteStatus, self).__init__()

        self.time = 0
        self.md5 = ""

    def fromFile(self, fileFullPath):
        ret = super(RemoteStatus, self).fromFile(fileFullPath)
        if ret != 0:
            return ret

        self.time = 0
        self.md5 = ""

        tmp = self.get("time")
        if tmp is not None:
            self.time = float(tmp)

        tmp = self.get("md5")
        if tmp is not None:
            self.md5 = str(tmp)

        logging.info("load remote status time[%f]", self.time)
        logging.info("load remote status md5[%s]", self.md5)
        return 0


def remove_file(f):
    if os.path.exists(f):
        logging.info("remove file [%s]", f)
        os.remove(f)


def remove_path(p):
    if os.path.isdir(p):
        logging.info("remove path [%s]", p)
        shutil.rmtree(p)


def shell_cmd(cmd):
    logging.info("run shell cmd[%s]", cmd)
    subp = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    sout, serr = subp.communicate()
    logging.info("shell retcode[%d]", subp.returncode)
    return subp.returncode, sout, serr


def clear_tmp(conf):
    logging.info("run proc clear_tmp")
    tmp_flag_file = conf.get("tmp", "tmp_flag_file")
    tmp_tar_file = conf.get("tmp", "tmp_tar_file")
    tmp_index = conf.get("tmp", "tmp_index")

    remove_file(tmp_flag_file)
    remove_file(tmp_tar_file)
    remove_path(tmp_index)


def check_remote_flag(status, remote_status):
    logging.info("run check_remote_flag")

    logging.info("remote index time[%f]", remote_status.time)
    logging.info("local last index time[%f]", status.lastUpdateTime)

    if remote_status.time > status.lastUpdateTime:
        logging.info("index need to update")
        return True
    else:
        logging.info("index do not need to update")
        return False


def get_remote_flag(conf):
    logging.info("run get_remote_flag")

    host = conf.get("indexsource", "host")
    user = conf.get("indexsource", "user")
    base_path = conf.get("indexsource", "base_path")
    flag = conf.get("indexsource", "tar_file_flag")

    remote_flag_file = os.path.join(base_path, flag)

    tmp_flag_file = conf.get("tmp", "tmp_flag_file")

    scp_flag_file = "%s %s@%s:%s %s" % (
        "scp -o BatchMode=yes -o StrictHostKeyChecking=no",
        user, host, remote_flag_file, tmp_flag_file)

    retcode, sout, serr = shell_cmd(scp_flag_file)
    if retcode != 0:
        logging.warn("sout : %s", sout)
        logging.warn("serr: %s", serr)
        return -1, None

    remote_status = RemoteStatus()
    ret = remote_status.fromFile(tmp_flag_file)
    if ret != 0:
        logging.warn("load remote status fail")
        return -2, None

    return 0, remote_status


def get_remote_index(conf, remote_status):
    logging.info("run get_remote_index")

    host = conf.get("indexsource", "host")
    user = conf.get("indexsource", "user")
    base_path = conf.get("indexsource", "base_path")
    tar = conf.get("indexsource", "tar_file")

    remote_tar_file = os.path.join(base_path, tar)

    tmp_tar_file = conf.get("tmp", "tmp_tar_file")

    scp_tar_file = "%s %s@%s:%s %s" % (
        "scp -o BatchMode=yes -o StrictHostKeyChecking=no",
        user, host, remote_tar_file, tmp_tar_file)

    retcode, sout, serr = shell_cmd(scp_tar_file)
    if retcode != 0:
        logging.warn("sout : %s", sout)
        logging.warn("serr: %s", serr)
        return -2

    md5file = open(tmp_tar_file, "rb")
    localmd5 = hashlib.md5(md5file.read()).hexdigest()
    md5file.close()
    logging.info("local file [%s] md5[%s]", (tmp_tar_file, localmd5))
    logging.info("remote file md5[%s]", remote_status.md5)
    if localmd5 != remote_status.md5:
        logging.warn("md5 check fail")
        return -3
    logging.info("md5 equal")
    return 0


def tar_extract(conf):
    logging.info("run tar_extract")

    tmp_index = conf.get("tmp", "tmp_index")
    tmp_tar_file = conf.get("tmp", "tmp_tar_file")

    tar = tarfile.open(tmp_tar_file, "r:gz")
    logging.info("extract [%s] to path [%s]", (tmp_tar_file, tmp_index))
    for name in tar.getnames():
        tar.extract(name, path=tmp_index)
        logging.info("extract file [%s]", name)
    tar.close()
    return 0


def index_replace(conf):
    logging.info("run index_replace")

    try:
        tmp_index = conf.get("tmp", "tmp_index")
        search_index = os.path.expandvars(conf.get("search", "index_data"))
        search_bak_path = os.path.expandvars(conf.get("search", "index_bak"))

        if not os.path.exists(search_bak_path):
            os.mkdir(search_bak_path)

        if os.path.exists(search_index):
            bak_name = "%s/%s_%s" % (search_bak_path,
                                     os.path.basename(tmp_index),
                                     time.strftime(
                                         "%Y%m%d_%H%M%S",
                                         time.localtime()))
            logging.info(
                "bak index mv [%s] to [%s]" %
                (search_index, bak_name))
            shutil.move(search_index, bak_name)

        logging.info(
            "update index mv [%s] to [%s]" %
            (tmp_index, search_index))
        shutil.move(tmp_index, search_index)

        return 0
    except Exception as e:
        logging.critical(str(e))
        return -1


def search_start(conf):
    start_cmd = conf.get("search", "start_cmd")
    retcode, sout, serr = shell_cmd(start_cmd)
    if retcode != 0:
        logging.warn("sout : %s", sout)
        logging.warn("serr: %s", serr)
        return -1
    return 0


def search_stop(conf):
    stop_cmd = conf.get("search", "stop_cmd")
    retcode, sout, serr = shell_cmd(stop_cmd)
    if retcode != 0:
        logging.warn("sout : %s", sout)
        logging.warn("serr: %s", serr)
        # stop失败不着急退出
    return 0


def rm_old_bak(conf):
    logging.info("run rm_old_bak")
    search_bak_path = os.path.expandvars(conf.get("search", "index_bak"))
    try:
        for d in os.listdir(search_bak_path):
            currPath = os.path.join(search_bak_path, d)
            if not os.path.isdir(currPath):
                continue
            file_modified = datetime.datetime.fromtimestamp(
                os.path.getctime(currPath))
            tdelta = datetime.timedelta(days=7)
            if datetime.datetime.now() - file_modified > tdelta:
                remove_path(currPath)
        return 0
    except Exception as e:
        logging.warn(str(e))
        return 0


class RunningFlag(object):

    def __init__(self, flag_file):
        self.flag_file = flag_file
        self.had_set_flag = False

    def __del__(self):
        if self.had_set_flag:
            self.clear_flag()

    def is_running(self):
        return os.path.exists(self.flag_file)

    def clear_flag(self):
        if os.path.exists(self.flag_file):
            remove_file(self.flag_file)

    def set_flag(self):
        with open(self.flag_file, "w+") as fh:
            fh.write("running")
            fh.close()
            self.had_set_flag = True


def run(conf):
    # 加载本地上次更新状态
    statFile = conf.get("status", "last_update")
    status = UpdateStatus()
    status.fromFile(statFile)

    clear_tmp(conf)

    ret, remote_status = get_remote_flag(conf)
    if ret != 0:
        logging.warn("get_remote_flag fail[%d]", ret)
        return ret

    need_update = check_remote_flag(status, remote_status)
    if not need_update:
        logging.info("no index update")
        logging.info("exit")
        return ret

    logging.info("now doing update index")

    ret = get_remote_index(conf, remote_status)
    if ret != 0:
        logging.warn("get_remote_index fail[%d]", ret)
        return ret

    ret = tar_extract(conf)
    if ret != 0:
        logging.warn("tar_extract fail[%d]", ret)
        return ret

    ret = search_stop(conf)
    if ret != 0:
        logging.warn("search_stop fail[%d]", ret)
        return ret

    ret = index_replace(conf)
    if ret != 0:
        logging.warn("index_replace fail[%d]", ret)
        return ret

    ret = search_start(conf)
    if ret != 0:
        logging.warn("search_start fail[%d]", ret)
        return ret

    rm_old_bak(conf)

    status.lastUpdateTime = remote_status.time
    status.toFile(statFile)
    return 0


def main():
    conf = ConfigParser.ConfigParser()
    running_flag = None
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--conf",
            dest="conf",
            required=True,
            help="configure file")
        args = parser.parse_args()

        conf.read(args.conf)
        logging.config.fileConfig(args.conf)
        # 自定义日志输出，发邮件
        logging.getLogger().addHandler(mail.MailLogHandler())

        running_flag = RunningFlag(conf.get("status", "running_flag"))
        if running_flag.is_running():
            logging.info("another process running,exit not")
            return -1

        running_flag.set_flag()

        ret = run(conf)
        if ret != 0:
            logging.warn("run fail[%d]", ret)
            return ret

        logging.info("all done")
    except Exception as e:
        logging.critical("get exception : %s", e)
    finally:
        mailto = conf.get("mail", "mailto")
        name = conf.get("mail", "name")
        mail.sendMail(
            "[IndexUpdate][%s]换库运行日志[%s]" %
            name,
            (socket.gethostname()),
            mailto)


if __name__ == '__main__':
    main()
