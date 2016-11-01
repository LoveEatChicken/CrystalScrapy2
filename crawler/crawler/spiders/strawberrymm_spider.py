#!/usr/bin/env python
# coding: utf-8
from bs4 import NavigableString
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from crawler.items import StrawberryMMItem
from bs4 import BeautifulSoup
import re

list_origin_url = 'https://cn.strawberrynet.com/skincare/masks/t/?groupId=4#catgid=1&brandid=0&typeid=123&typeList=&funcid=0&lineid=&groupid=4&sort=popularity&page=%d&filterids=&method=1&othcatgid=0&viewtype=grid&type=productlist&brandlist=&totalPage=532'
detail_origin_url = 'https://cn.strawberrynet.com/skincare%s'
class StrawberrySpider(Spider):

    name = "strawberrymm"
    allowed_domains = ["strawberrynet.com"]

    def start_requests(self):
        # 最大页码
        # MAX_PAGE_COUNT = 7;
        MAX_PAGE_COUNT = 2;
        for page in range(1,MAX_PAGE_COUNT):
            url =list_origin_url % page
            print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        href_tags = soup.find_all('a', class_="productlistImg col-xs-11 img-link")
        for href_tag in href_tags:

            href = href_tag["href"]
            m = re.match(r'([\s\S]*)([0-9]+)(/)', href)
            item['id'] = m.group(2)
            print 'itemid -------------- %d' % int(item['id'])
            item = CommonItem()
            # item_link = 'https://cn.strawberrynet.com/skincare/dermaheal/cosmeceutical-mask-pack/179866/'
            item_link = detail_origin_url + href
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            item['url'] = item_link
            item['source'] = 'strawberrynet.com'
            yield Request(item_link, callback=self.parse_strawberry_item, meta={'item': item})

    def parse_strawberry_item(self, reponse):
        """解析Strawberry Item"""
        data = reponse.body
        soup = BeautifulSoup(data, "html5lib")
        item = reponse.meta['item']

        strawberry_item = StrawberryMMItem()

        # title_tag = soup.find('dt', class_="product-title")
        # kaola_item['title'] = title_tag.text
        #
        # goods_tag = soup.find('ul', class_='goods_parameter')
        # kaola_item['brand'] = Parse_Util.get_parse_value(goods_tag, u'商品品牌：')
        # kaola_item['product_name'] = Parse_Util.get_parse_value(goods_tag, u'品名：')
        # kaola_item['good_detail'] = Parse_Util.make_up_dic(goods_tag)
        # item['other_parameter'] = kaola_item

        yield item