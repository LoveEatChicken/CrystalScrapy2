#!/usr/bin/env python
# coding: utf-8

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from utils import db
import sys
import json


def start_spider(template_id):
    user = 'iwant'
    pw = 'iwant@201506'
    host = '10.10.139.235'
    port = 3306
    database = 'iwant'
    db.create_engine(user, pw, database, host, port)

    data_source = db.select_one('select id,spider_name,domain,classify,subclass,site,source,des_tasks from des_template where id = ?', template_id)
    if not data_source:
        return
    tasks = json.loads(data_source.des_tasks)
    db.update('update des_task set status=? where id=?', 1, tasks['page_crawl'])
    try:
        process = CrawlerProcess(get_project_settings())

        # 'followall' is the name of one of the spiders of the project.
        process.crawl(data_source.spider_name,**data_source)
        process.start()  # the script will block here until the crawling is finished
    except:
        db.update('update des_task set status=? where id=?', 3, tasks['page_crawl'])

    db.update('update des_task set status=? where id=?', 2, tasks['page_crawl'])





####main#######---------------
if __name__ == '__main__':
    args = sys.argv
    if len(args) < 2:
        sys.exit()
    start_spider(args[1])