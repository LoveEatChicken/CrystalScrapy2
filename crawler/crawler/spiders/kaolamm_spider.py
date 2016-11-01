#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from crawler.items import KaoLaMMItem
from bs4 import BeautifulSoup
import re
from crawler.utils.parse_util import Parse_Util

list_origin_url = 'http://www.kaola.com/category/1471.html?pageSize=60&pageNo=%d'
detail_origin_url = 'http://www.kaola.com'
class KaoLaSpider(Spider):

    name = "kaolamm"
    allowed_domains = ["kaola.com"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 6;
        # MAX_PAGE_COUNT = 2;
        for page in range(1,MAX_PAGE_COUNT):
            url =list_origin_url % page
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        #print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        sites = soup.find_all('div', class_="titlewrap")
        for site in sites:

            id = site.find('a', class_="title")["href"]
            item = CommonItem()
            # item_link = 'http://www.kaola.com/product/17182.html'
            item_link = detail_origin_url + id

            m = re.match(r'(http://www.kaola.com/product/)(\d+)(.html)',item_link)
            item['id'] = m.group(2)
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            item['url'] = item_link
            item['source'] = 'kaola.com'
            yield Request(item_link, callback=self.parse_kaola_item, meta={'item': item})

    def parse_kaola_item(self, reponse):
        """解析Kaola Item"""
        data = reponse.body
        soup = BeautifulSoup(data, "html5lib")
        item = reponse.meta['item']

        kaola_item = KaoLaMMItem()

        title_tag = soup.find('dt', class_="product-title")
        kaola_item['title'] = title_tag.text

        goods_tag = soup.find('ul', class_='goods_parameter')
        kaola_item['brand'] = Parse_Util.get_parse_value(goods_tag, u'商品品牌：')
        kaola_item['product_name'] = Parse_Util.get_parse_value(goods_tag, u'品名：')
        kaola_item['good_detail'] = Parse_Util.make_up_dic(goods_tag)
        item['other_parameter'] = kaola_item

        yield item