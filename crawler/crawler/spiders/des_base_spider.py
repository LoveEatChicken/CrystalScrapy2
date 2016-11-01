#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider

class BaseSpider(Spider):

    def __init__(self, **kw):
        super(BaseSpider, self).__init__(**kw)
        self.domain = kw.get('domain')
        self.site =kw.get('site')
        self.source = kw.get('source')
        self.classify = kw.get('classify')
        self.subclass = kw.get('subclass')
        self.template_id = kw.get('id')
