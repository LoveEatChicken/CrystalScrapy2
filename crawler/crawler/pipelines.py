# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json, codecs
from scrapy import signals
from scrapy import log
from scrapy.exporters import JsonLinesItemExporter
from scrapy.exporters import CsvItemExporter
from exporters import DecodeJsonLinesItemExporter
from utils import dj_database_url
import MySQLdb
from twisted.internet import defer
from twisted.enterprise import adbapi
from scrapy.exceptions import NotConfigured
from scrapy.exceptions import DropItem
import traceback
from utils import uuid_util
from scrapy.item import Item
LOCAL_ABSOLUTE_PATH = '/data/home/iwant/code20/crawler/spider_jls/'
class DataCleanPipeline(object):
    '''
    数据粗清洗,补齐uuid和异常,去除换行和头尾空格
    '''
    def process_item(self, item, spider):
        item['exception'] = {}
        item['exception_code'] = 0
        item['uuid'] = uuid_util.next_id()
        item['exception'],item['exception_code'] =self.cleandata(item)
        if item['id'] and item['source']:
            item['uuid'] = item['source']+item['id']
        return item

    def cleandata(self,item,exception = {},exception_code = 0):
        '''
        数据清洗
        :param item:
        :param exception:
        :param exception_code:
        :return:
        '''
        for k, v in item.iteritems():
            # key = k.decode('utf-8')
            if (v is None) or (v == ''):
                exception_code = 1
                exception[k] = 'None'
            elif isinstance(v, Item):
                self.cleandata(v, exception, exception_code)
            elif isinstance(v,(str,unicode)):
                item[k] = self.format_string(v)
        return exception,exception_code

    # def format_string(self,str):
    #     # result = str.strip(u'\n').strip(u'\r').strip(u'\t').strip('\n').strip('\r').strip('\t')
    #     result = str.strip()
    #     return result
    def format_string(self,str):
        result = str.replace("\t", " ").replace("\n", " ").replace("\r", " ").strip()
        result = " ".join(result.split())

        return result

class JsonLinePipeLine(object):
    """用于将对象按行存储成json"""

    def __init__(self):
        self.files = {}

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline


    def spider_opened(self, spider):
        file = codecs.open('%s%s_products.jl' % (LOCAL_ABSOLUTE_PATH, spider.name), 'w+', encoding='utf-8')
        self.files[spider] = file
        self.exporter = DecodeJsonLinesItemExporter(file,encoding='utf-8')
        self.exporter.start_exporting()


    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        file = self.files.pop(spider)
        file.close()


    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item


class CsvPipeLine(object):
    """用于将数据存储城csv,未经过测试"""
    def __init__(self):
        self.files = {}

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        file = open('%s_products.csv' % spider.name, 'w+b')
        self.files[spider] = file
        self.exporter = CsvItemExporter(file,encoding='utf-8')
        self.exporter.start_exporting()

    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        file = self.files.pop(spider)
        file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item


class MySqlPipeLine(object):
    """用于将数据存储进入des_raw_parsed_data"""

    def __init__(self, mysql_url):
        """Opens a MySQL connection pool"""

        # Store the url for future reference
        self.mysql_url = mysql_url
        # Report connection error only once
        self.report_connection_error = True

        # Parse MySQL URL and try to initialize a connection
        conn_kwargs = MySqlPipeLine.parse_mysql_url(mysql_url)
        self.dbpool = adbapi.ConnectionPool('MySQLdb',
                                            charset='utf8',
                                            use_unicode=True,
                                            connect_timeout=5,
                                            **conn_kwargs)

    @classmethod
    def from_crawler(cls, crawler):
        # Get MySQL URL from settings
        mysql_url = crawler.settings.get('MYSQL_PIPELINE_URL', None)

        # If doesn't exist, disable the pipeline
        if not mysql_url:
            raise NotConfigured

        # Create the class
        pipeline = cls(mysql_url)
        # crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        # crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def close_spider(self, spider):
        self.dbpool.close()

    def process_item(self, item, spider):
        if spider.name is "xzwxz2" or spider.name is "letianmm":
            """Processes the item. Does insert into MySQL"""
            query = self.dbpool.runInteraction(self.do_replace, item)
            query.addErrback(self.handle_error)
            return item
        raise DropItem
        # defer.returnValue(item)

        # logger = spider.logger
        #
        # try:
        #     yield self.dbpool.runInteraction(self.do_replace, item)
        # except MySQLdb.OperationalError:
        #     if self.report_connection_error:
        #         logger.error("Can't connect to MySQL: %s" % self.mysql_url)
        #         self.report_connection_error = False
        # except:
        #     print traceback.format_exc()

        # Return the item for the next stage
        # defer.returnValue(item)


    def do_replace(self, tx, item):
        """Does the actual REPLACE INTO"""
        sql = """REPLACE INTO des_raw_parsed_data (id, content, url, source, exception_detail, exception_code, site, template_id, domain, classify, subclass)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        content = json.dumps(dict(item["other_parameter"]),ensure_ascii=False)
        # if content:
        #     content = content.decode('unicode_escape')
        args = (
            item["uuid"],
            content,
            item["url"],
            item["source"],
            json.dumps(item["exception"],ensure_ascii=False),
            item["exception_code"],
            item["site"],
            item["template_id"],
            item["domain"],
            item["classify"],
            item["subclass"]
        )

        tx.execute(sql, args)

    def handle_error(self, e):
        # print e
        log.err(e)

    @staticmethod
    def parse_mysql_url(mysql_url):
        """
        Parses mysql url and prepares arguments for
        adbapi.ConnectionPool()
        """

        params = dj_database_url.parse(mysql_url)

        conn_kwargs = {}
        conn_kwargs['host'] = params['HOST']
        conn_kwargs['user'] = params['USER']
        conn_kwargs['passwd'] = params['PASSWORD']
        conn_kwargs['db'] = params['NAME']
        conn_kwargs['port'] = params['PORT']

        # Remove items with empty values
        conn_kwargs = dict((k, v) for k, v in conn_kwargs.iteritems() if v)

        return conn_kwargs