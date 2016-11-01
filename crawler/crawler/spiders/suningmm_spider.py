#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
import re
import json
from crawler.utils.parse_util import Parse_Util

list_origin_url = 'http://list.suning.com/0-362506-%d.html'
price_origin_url = 'http://pas.suning.com/nspcsale_0_000000000%s_000000000%s_%s_10_010_0100101_329503_1000000_9017_10106_Z001.html'
class SuningSpider(Spider):

    name = "suningmm"
    allowed_domains = ["suning.com"]

    def start_requests(self):
        # 最大页码
        # MAX_PAGE_COUNT = 101;
        MAX_PAGE_COUNT = 4;
        for page in range(1,MAX_PAGE_COUNT):
            url =list_origin_url % page
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        #print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        pro_div_tags = soup.find_all('div', class_='res-opt')
        for pro_div_tag in pro_div_tags:
            pro_a_tag = pro_div_tag.find('a', recursive=False)
            item_link = pro_a_tag['buyproduct']
            item_link = 'http://product.suning.com/0070146044/171306666.html'
            item = CommonItem()

            m = re.match(r'(http://product.suning.com/)([\s\S]*)(.html)', item_link)
            item['id'] = m.group(2)
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            item['url'] = item_link
            item['source'] = 'suning.com'
            yield Request(item_link, callback=self.parse_suning_item, meta={'item': item})

    def parse_suning_item(self, response):
        """解析Suning Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        pro_parameter_dic = {}

        zy_tag = soup.html.find('span',id='itemNameZy')
        if zy_tag != None:
            zy_tag.extract()
        title_tag = soup.find('h1', id="itemDisplayName")
        pro_parameter_dic['title'] = Parse_Util.get_no_space_string(title_tag.text)
        #class = pro-para-tbl
        bgqd_tag = soup.find('table', id='bzqd_tag')
        if bgqd_tag != None:
            bgqd_tag.extract()
        table_tag = soup.find('table', id='itemParameter')
        # print 'tabletag ---------- %s' % table_tag
        if table_tag == None:
            print 'sssssssss -------- tabletag is None'
            table_tag = soup.html.find('table', id='pro-para-tbl')
            print 'pro-para-tbl ----- %s' % table_tag
        body_tag = table_tag.find('tbody')
        tr_tags = body_tag.find_all('tr')
        # print 'sssssssssss -------- %s' % soup.html.find_all('th')
        #th标签从html树移除
        for th_tag in soup.html.find_all('th'):
            th_tag.extract()
        # print 'zzzzzzzzzzz -------- %s' % soup.html.find_all('th')
        for tr_tag in tr_tags:
            item_dic_key = 'key'
            item_dic_value = 'value'
            # is_brand_tag = False
            for i, tr_tag_str in enumerate(tr_tag.stripped_strings):
                # print 'index --- %s :tr_tag_str ------- %s' % (i, tr_tag_str)
                if i == 0:
                    item_dic_key = tr_tag_str
                if i == 1:
                    item_dic_value = tr_tag_str
            pro_parameter_dic[item_dic_key] = item_dic_value

        del pro_parameter_dic['key']
        item['other_parameter'] = pro_parameter_dic

        p = re.match(r'(\d+)(/)(\d+)', str(item['id']))
        vendorCode = p.group(1)
        partNumber = p.group(3)
        price_url = price_origin_url % (partNumber, partNumber, vendorCode)
        # print 'ooooooooooooooooo ------------------- %s' % price_url
        yield Request(price_url, callback=self.parse_price_item, meta={'item': item})

    def parse_price_item(self, response):
        pc_data = response.body
        pc_data = pc_data.decode('UTF-8')
        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        json_data = self.get_json_str(pc_data)
        data = json.loads(json_data, 'UTF-8')

        pro_parameter_dic['price'] = data['data']['price']['saleInfo'][0]['netPrice']
        pro_parameter_dic['promotion_price'] = data['data']['price']['saleInfo'][0]['promotionPrice']

        yield item

    def get_json_str(self, response_data):
        # print 'eeeeeeee ----------- %s' % response_data
        m = re.match(r'(pcData\()([\s\S]*)(\))', response_data)
        return m.group(2)

