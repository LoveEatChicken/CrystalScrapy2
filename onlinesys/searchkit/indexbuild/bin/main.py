#!/usr/bin/env python
# encoding=utf-8
""""
main.py
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.append("../pythonlib")
sys.path.append("./pythonlib")
import argparse
import ConfigParser
import logging
import logging.config
import subprocess
import os
import os.path
import json
import tarfile
import hashlib
import time
import shutil
import datetime

from dbreader import DBReader
import mail


def remove_file(f):
    if os.path.exists(f):
        logging.info("remove file [%s]" % f)
        os.remove(f)


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


def indexbuild(conf):
    mysql_tmpfile = os.path.join(os.getcwd(), conf.get('mysql', 'tmpfile'))
    server_home = os.path.expandvars(conf.get("search", "server_home"))
    so_path = os.path.join(server_home, "bin")
    ld_library_path = "%s:%s" % (
        so_path,
        os.path.expandvars("$LD_LIBRARY_PATH")
    )
    buildcmd = "cd %s;export LD_LIBRARY_PATH=%s;%s -b -d '%s'" % (
        server_home,
        ld_library_path,
        os.path.expandvars(conf.get("search", "bin_name")),
        mysql_tmpfile)
    logging.info("begin build index cmd [%s]" % buildcmd)
    subp = subprocess.Popen(buildcmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    sout, serr = subp.communicate()
    logging.info("build index retcode[%d]" % subp.returncode)
    if subp.returncode != 0:
        logging.critical("run as stdout : [%s]" % sout.strip('\n'))
        logging.critical("run as stderr: [%s]" % serr.strip('\n'))
        logging.critical("build index fail")
        return -1

    logging.info("checking index status")

    idstatfile = os.path.expandvars(conf.get("search", "id_stat"))
    if not os.path.isfile(idstatfile):
        logging.critical("index id file [%s] not exist" % idstatfile)
        return -1
    idstatfh = open(idstatfile, "r")
    if idstatfh is None:
        logging.critical("open file [%s] fail" % idstatfile)
        return -2
    text = idstatfh.read()

    idobj = json.loads(text)
    if idobj is None:
        logging.critical("file [%s] content not json" % idstatfile)
        return -3
    logging.info("[%s][MaxInId:%d]" % (idstatfile, idobj["MaxInId"]))
    logging.info("[%s][CurId:%d]" % (idstatfile, idobj["CurId"]))

    min_succ_index_id = int(conf.get("indexbuild", "min_succ_index_id"))
    logging.info(
        "conf[indexbuild][min_succ_index_id] = %d" %
        (min_succ_index_id))

    if int(idobj["CurId"]) < int(min_succ_index_id):
        logging.critical("succ index id not enough , index build fail")
        return -4

    logging.info("check idstat succ")
    return 0


def bakindex(conf):
    bak_path = conf.get("indexbuild", "bak_path")

    # remove old file
    for dirpath, dirnames, filenames in os.walk(bak_path):
        for f in filenames:
            currfile = os.path.join(dirpath, f)
            file_modified = datetime.datetime.fromtimestamp(
                os.path.getmtime(currfile))
            tdelta = datetime.timedelta(days=7)
            if datetime.datetime.now() - file_modified > tdelta:
                logging.info(
                    "remove old bak file [%s]" %
                    currfile)
                os.remove(currfile)

    tar_file = conf.get("indexbuild", "tar_file")
    if not os.path.isfile(tar_file):
        logging.info("no old index file [%s]" % tar_file)
        return 0
    newname = "%s/%s_%s" % (bak_path,
                            os.path.basename(tar_file),
                            time.strftime(
                                "%Y%m%d_%H%M%S",
                                time.localtime()))

    logging.info("index bak new name [%s]" % newname)
    shutil.move(tar_file, newname)

    return 0


def tarindex(conf):
    tar_file = conf.get("indexbuild", "tar_file")
    tar_file_flag = conf.get("indexbuild", "tar_file_flag")

    if os.path.isfile(tar_file_flag):
        logging.info("rm old tar_file_flag[%s]" % tar_file_flag)
        os.remove(tar_file_flag)

    logging.info("tar file [%s] begin" % (tar_file))
    tar = tarfile.open(tar_file, "w:gz")
    indexdir = os.path.expandvars(conf.get("search", "index_name"))
    tar.add(indexdir, arcname="")
    tar.close()
    logging.info("tar file [%s] finish" % (tar_file))

    flag = dict()
    flag["file"] = tar_file

    md5file = open(tar_file, "rb")
    flag["md5"] = hashlib.md5(md5file.read()).hexdigest()
    md5file.close()

    flag["time"] = time.time()

    with open(tar_file_flag, "w") as outfh:
        json.dump(flag, outfh, ensure_ascii=False)

    logging.info("tar file flag [%s]" % (tar_file_flag))

    return 0


def main():
    conf = ConfigParser.ConfigParser()
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

        db = DBReader()
        db.Init(conf)
        ret = db.DumpAll(conf)
        if ret < 0:
            logging.critical("db reader dump data fail")
            return ret

        ret = indexbuild(conf)
        if ret < 0:
            logging.critical("indexbuild fail")
            return ret

        ret = bakindex(conf)
        if ret < 0:
            logging.critical("bakindex fail")
            return ret

        ret = tarindex(conf)
        if ret < 0:
            logging.critical("tarindex fail")
            return ret

    except Exception as e:
        logging.critical("get exception : %s", e)
    finally:
        mailto = conf.get("mail", "mailto")
        program = conf.get("main", "program")
        mail.sendMail("[%s][IndexBuild]建库运行日志" % program, mailto)


if __name__ == '__main__':
    main()
