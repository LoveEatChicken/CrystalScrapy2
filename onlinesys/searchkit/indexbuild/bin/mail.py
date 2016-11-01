#!/usr/bin/env python
# encoding=utf-8
""""
mail.py
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import getpass
import socket
from email.mime.text import MIMEText
from email.Header import Header
from subprocess import Popen, PIPE
import logging

infolist = list()


def addInfo(info):
    infolist.append(str(info))


def mailfrom():
    return "%s@%s" % (getpass.getuser(), socket.gethostname())


def sendMail(subject, mailto):
    mailCont = "\r\n".join(infolist)

    msg = MIMEText(mailCont, _charset="utf-8")
    msg["From"] = mailfrom()
    msg["To"] = mailto
    msg["Subject"] = Header(subject, "utf-8")
    p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
    p.communicate(msg.as_string())


class MailLogHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)

        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s : %(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        addInfo(msg)


def main():
    addInfo("test")
    addInfo("abc")
    addInfo("中文")
    sendMail("[search][test]", "honggengwei@baidu.com")

if __name__ == '__main__':
    main()
