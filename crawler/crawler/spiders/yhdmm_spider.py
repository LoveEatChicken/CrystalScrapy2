#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import YHDMMItem
from bs4 import BeautifulSoup
import re
from crawler.utils.parse_util import Parse_Util

class YHDSpider(Spider):
    name = "yhdmm"
    allowed_domains = ["yhd.com"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 36;
        # MAX_PAGE_COUNT = 2;
        for page in range(35,MAX_PAGE_COUNT):
            url =('http://list.yhd.com/c38329-0-132386/b/?tc=3.0.9.38329.3&ti=1RJROd#page=%d&sort=1') % page
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        sites = soup.find_all('div', class_="proImg")
        for site in sites:

            id = site.find('a', class_="img")["pmid"]
           # print 'idddddddddddddddddddddd----------- %d' % int(id)
            item = YHDMMItem()
            #item_link = 'http://item.yhd.com/item/%d?tc=3.0.5.60683254.1&ti=HYTCn2' % int(29689120)
            item_link = 'http://item.yhd.com/item/%d?tc=3.0.5.23139757.53&tp=52.38329.108.2093.1.LT7^^aO-10-6x7wt&ti=GUSBaw' % int(id)
            # item['id'] = id
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            item['url'] = item_link
            # item['source'] = 0
            yield Request(item_link, callback=self.parse_yhd_item, meta={'item': item})

    def parse_yhd_item(self, reponse):
        """解析tmall Item"""
        data = reponse.body
        soup = BeautifulSoup(data, "html5lib")
        item = reponse.meta['item']

        title_tag = soup.find('h1', id="productMainName")
        item['title'] = title_tag.text

        is_proprietary_trading = False
        source_tag = soup.find('p', attrs={'class': 'add_02'})
        # print 'sssssssssssource_tag.string    %s' % source_tag.string
        # print 'ttttttttttsource_tag.text    %s' % source_tag.text
        if source_tag.text.strip().startswith(u'本商品由1号店自营提供'):
            # print 'sssssssssssssssssssssss本商品由1号店自营提供'
            is_proprietary_trading = True

        else:
            pass


        if is_proprietary_trading:

            ul_tag = soup.find('ul', attrs={'class': 'ull'})

            brand_name = Parse_Util.get_parse_value(ul_tag, u'【产品品牌】：')
            if brand_name == 'None':

                brand_name = Parse_Util.get_parse_value(ul_tag, u'【品牌名称】：')

            if brand_name == 'None':

                dl_tag = soup.find('dl', attrs={'class': 'des_info clearfix'})
                brand_name = self.get_brand(dl_tag)

            product_name = Parse_Util.get_parse_value(ul_tag, u'【产品名称】：')
            if product_name == 'None':

                product_name = Parse_Util.get_parse_value(ul_tag, u'【商品名称】：')
            if product_name == 'None':

                product_name = Parse_Util.get_parse_value(ul_tag, u'【名称】：')

            item['brand'] = brand_name
            item['product_name'] = product_name
            item['source'] = 1

        else:

            good_tag = soup.find('dl', class_="des_info clearfix")
            item['brand'] = self.get_brand(good_tag)
            item['source'] = 0

        yield item

    def get_brand(self, parentNode):

        value = 'None'
        if hasattr(parentNode, 'find'):
            brand_tag = parentNode.find(title=re.compile(u'品牌：'))
            if not brand_tag.text is None:

                value = brand_tag.text[4:]

            return value
