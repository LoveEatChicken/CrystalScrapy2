#!/usr/bin/env python
# coding: utf-8

from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.selector import Selector
from crawler.items import JDMMItem
from bs4 import BeautifulSoup
import re


class TestSpider(Spider):

    name = "test"
    allowed_domains = ["jd.com","jd.hk"]

    def start_requests(self):
        # 最大页码
        # MAX_PAGE_COUNT = 262;
        MAX_PAGE_COUNT = 2;
        for page in range(1,MAX_PAGE_COUNT):
            url ='http://list.jd.com/list.html?cat=1316,1381,1392&page=%d&trans=1&JL=6_0_0#J_main' % page
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        sites = soup.find_all('div', class_="gl-i-wrap j-sku-item")
        for site in sites:
            id = site['data-sku']
            tags =site.find('div',class_="p-icons J-pro-icons")
            is_word_wide = False
            for tag in tags:
                if tag.string ==u"全球购" :
                    is_word_wide = True
                    break
            item = JDMMItem()
            item['id'] = id

            if is_word_wide:
                item_link = 'https://item.jd.hk/%s.html' % id
                item['source'] = JDMMItem.SOURCE_TYPE_WORDWIDE
                yield Request(item_link, callback=self.parse_word_wide_item, meta={'item': item})
            else:
                item_link = 'http://item.jd.com/%s.html' % id
                item['source'] = JDMMItem.SOURCE_TYPE_NORMAL
                yield Request(item_link, callback=self.parse_jd_item, meta={'item': item})




    def parse_jd_item(self, response):
        """解析普通jd Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']

        title_tag = soup.find('div', id="name")
        title = 'error'
        for child in title_tag.children:
            if child is None:
                continue
            if child.name is None:
                continue
            if child.name == u"h1":
                title = child.string
                break

        item['title'] = title
        yield item

    def parse_word_wide_item(self,response):
        """解析全球购ITEM"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']

        title_tag = soup.find('div', id="name")
        title = 'error'
        for child in title_tag.children:
            if child is None:
                continue
            if child.name is None:
                continue
            if child.name == u"h1":
                i = 0
                for str in child.stripped_strings:
                    if i ==1:
                        title = str
                        break
                    i+=1
                break

        item['title'] = title
        yield item







        # yield scrapy.Request(item_details_url, self.parse_details, meta={'item': item})

    # def parse_details(self, response):
    #     item = response.meta['item']
    #     return item