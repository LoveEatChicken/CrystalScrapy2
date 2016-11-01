#!/usr/bin/env python
# encoding=utf-8
""""
dbreader.py
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.append("../pythonlib")
sys.path.append("./pythonlib")
import mysql.connector
import logging
import json


class DBReader(object):

    def __init__(self):
        pass

    def __del__(self):
        self.conn.close()

    def Init(self, conf):
        self.mysql_host = conf.get("mysql", "host")
        self.mysql_port = conf.get("mysql", "port")
        self.mysql_user = conf.get("mysql", "user")
        self.mysql_password = conf.get("mysql", "password")
        self.mysql_database = conf.get("mysql", "database")
        self.mysql_tmpfile = conf.get('mysql', 'tmpfile')
        self.mysql_sql = conf.get("mysql", "sql")

        self.conn = mysql.connector.connect(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_database)

    def DumpAll(self, conf):
        logging.info("begin DumpAll")

        cursor = self.conn.cursor()
        tmpfh = None
        try:
            tmpfh = open(self.mysql_tmpfile, "w")
            if tmpfh is None:
                logging.fatal("open file[%s] fail" % self.mysql_tmpfile)
                return -1

            logging.info("begin execute sql [%s]" % self.mysql_sql)
            cursor.execute(self.mysql_sql)
            res_all = cursor.fetchall()
            logging.info("end excute , finish fatchall")
            if res_all is None:
                return -1

            program = conf.get("main", "program")
            doc_list = list()

            if program == "qasearch":
                import qasearch
                doc_list = qasearch.run(conf, res_all)
            elif program == "fmsearch":
                import fmsearch
                doc_list = fmsearch.run(conf, res_all)
            else:
                logging.fatal("unknow program : %s", program)
                return -1

            for doc in doc_list:
                tmpfh.write(json.dumps(doc, ensure_ascii=False)+"\n")

            logging.info("dump total [%d] data" % len(doc_list))
            logging.info("save all data in [%s]" % self.mysql_tmpfile)

            return 0

        except mysql.connector.Error as e:
            logging.warning(e)
            return -2
        except Exception as e:
            logging.warning(e)
            return -2
        finally:
            if tmpfh is not None:
                tmpfh.close()
            cursor.close()


def main():
    print 'run main func'

if __name__ == '__main__':
    main()
