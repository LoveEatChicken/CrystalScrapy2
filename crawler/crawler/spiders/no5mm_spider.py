#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
import re
import string
from crawler.utils.parse_util import Parse_Util

list_origin_url = 'http://category.dangdang.com/pg%d-cid4009711.html'
detail_origin_url = 'http://product.dangdang.com/%d.html'
class No5Spider(Spider):

    name = "dangdangmm"
    allowed_domains = ["dangdang.com"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 48;
        # MAX_PAGE_COUNT = 2;
        for page in range(1, MAX_PAGE_COUNT):
            url = list_origin_url % page
            # url = 'http://category.dangdang.com/pg2-cid4009711.html'
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        #找到所有商品item标签
        item_ul_tag = soup.find('ul', id='component_0__0__1499')
        item_li_tags = item_ul_tag.find_all('li', recursive=False)
        for li_tag in item_li_tags:
            item_id = li_tag['id']
            item = CommonItem()
            item['id'] = item_id
            item_link = detail_origin_url % int(item_id)
            item['url'] = item_link
            item['source'] = 'dangdang.com'
            yield Request(item_link, callback=self.parse_dangdang_item, meta={'item': item})

    def parse_dangdang_item(self, response):
        """解析DangDang Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        dangdang_item = DangDangMMItem()
        title_tag = soup.find('div', attrs={'name': 'Title_pub'})
        if title_tag == None:
            title_tag = soup.find('div', class_='name_info')

        h1_tag = title_tag.find('h1', recursive=False)
        if h1_tag.children != None:
            span_tags = h1_tag.find_all('span')
            for span_tag in span_tags:
                span_tag.extract()
        # print h1_tag
        dangdang_item['title'] = h1_tag.text

        detail_all_tag = soup.find('div', id='detail_all')
        textarea_tag = detail_all_tag.find('textarea')
        detail_tag_list = textarea_tag.contents
        list_str = ''.join(detail_tag_list)
        list_soup = BeautifulSoup(list_str, "html5lib")

        good_detail_dic = {}
        detail_tags = list_soup.find_all('div', class_='mall_goods_foursort_style_frame')
        for detail_tag in detail_tags:
            if string.find(detail_tag.text, u'：')!= -1 and detail_tag.text[-1] != u'：':
            #     p = re.compile('\s+')
            #     no_space_string = re.sub(p, '', li_str)
                parameterList = detail_tag.text.split(u'：')
                good_detail_dic[parameterList[0]] = parameterList[1]
                if detail_tag.text.strip().startswith(u'品牌：'):
                    dangdang_item['brand'] = detail_tag.text.strip(u'品牌：')

            # print 'zzzzzzzzzzzzzzzzzzzzzzzzz ------------ %s' % detail_tag.text
        dangdang_item['good_detail'] = good_detail_dic
        item['other_parameter'] = dangdang_item

        yield item