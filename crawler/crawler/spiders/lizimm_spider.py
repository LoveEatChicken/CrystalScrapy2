#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
import re
import string
import json
from crawler.utils.parse_util import Parse_Util

pre_list_url = 'http://www.lizi.com/itemSearch/search?content=%E9%9D%A2%E8%86%9C&'
suf_list_origin_url = 'offset=%d&max=40'
detail_origin_url = 'http://www.lizi.com/product-%d.html'
price_origin_url = 'http://www.lizi.com/item/item_detail?itemId='
class LiZiSpider(Spider):

    name = "lizimm"
    allowed_domains = ["lizi.com"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 11;
        # MAX_PAGE_COUNT = 1;
        for page in range(0, MAX_PAGE_COUNT):
            suf_list_url = suf_list_origin_url % (page*40)
            url = pre_list_url + suf_list_url
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):

        data = response.body
        #print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        pro_group_tag = soup.find('div', id='productlist')
        pro_a_tags = pro_group_tag.find_all('a', target="_blank")
        for pro_a_tag in pro_a_tags:

            item = CommonItem()
            # item_link = 'http://www.lizi.com/product-742154215.html'
            item_link = pro_a_tag['href']
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            m = re.match(r'([\s\S]*)([0-9]+)(.html)', item_link)
            item_id = m.group(2)
            item['id'] = item_id
            item['url'] = item_link
            item['source'] = 'lizi.com'
            yield Request(item_link, callback=self.parse_lizi_item, meta={'item': item})

    def parse_lizi_item(self, response):
        """解析Lizi Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        pro_parameter_dic = {}

        title_dt_tag = soup.find('dt', class_="product_name")
        title_tag = title_dt_tag.find('h1', recursive=False)
        # title_i_tag = title_tag.find('i', recursive=False)
        # if title_i_tag != None:
        #     title_i_tag.extract()
        pro_parameter_dic['title'] = Parse_Util.get_no_space_string(title_tag.text)

        detail_info_tag = soup.find('td', class_='op')
        detail_tbody_tag = detail_info_tag.find('tbody')
        # print 'zzzzzzzzzzzzzzz ------------ %s' % detail_tbody_tag
        detail_tags = detail_tbody_tag.find_all('tr')
        for tr_tag in detail_tags:
            # print 'liiiiistr --------- %s' % tr_tag.text
            no_space_string = tr_tag.text.replace("\t", " ").replace("\n", " ").replace("\r", " ").strip()
            no_space_string = " ".join(no_space_string.split())
            # print 'ssssssssssss %s' % no_space_string
            if string.find(no_space_string, u'：')!= -1 and no_space_string[-1] != u'：':
                parameterList = no_space_string.split(u'：')
                pro_parameter_dic[parameterList[0]] = parameterList[1]
                # PM - Oriented
                # if no_space_string.strip().startswith(u'所属品牌：'):
                #     lizi_item['brand'] = no_space_string.strip(u'所属品牌：')
                # if no_space_string.strip().startswith(u'商品名称：'):
                #     lizi_item['product_name'] = no_space_string.strip(u'商品名称：')
                #     # print 'zzzzzzzzzzzzzzzzzzzzzzzzz ------------ %s' % detail_tag.text
        #
        # price_info_tag = soup.find('dd', id='item_info')
        # print 'priceeeeeeeeeeeeee ------------------- %s' % price_info_tag

        item['other_parameter'] = pro_parameter_dic

        script_tags = soup.find_all('script')
        # print 'zzzdsadfadfasdfasf ------------- %s' % script_tags[3]
        script_id_tag = script_tags[3]
        origin_data = Parse_Util.get_no_space_string(script_id_tag.text)
        p = re.match(r'([\s\S]*id:)([\s\S]*)(, cover[\s\S]*)', origin_data)
        price_id_str = p.group(2).replace('\'', " ")
        price_id_str = " ".join(price_id_str.split())
        price_link = price_origin_url + str(price_id_str)
        # print 'rrrrrrrrrrr -------------- %s' % price_link
        yield Request(price_link, callback=self.parse_price_item, meta={'item': item})

    def parse_price_item(self, response):
        data = response.body
        data = data.decode('UTF-8')
        json_data = json.loads(data, 'UTF-8')

        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        pro_parameter_dic['price'] = json_data['skus'][0]['price']
        pro_parameter_dic['comment'] = json_data['comment']
        pro_parameter_dic['salesVolume'] = json_data['salesVolume']

        yield item




