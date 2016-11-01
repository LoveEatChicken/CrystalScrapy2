#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
import re
import json
from crawler.utils.parse_util import Parse_Util

list_origin_url = 'http://cn.memebox.com/mmzq?p=%d'
price_origin_url = 'https://search.cn.memebox.com/global/price?productIds=%s'
class MeMeBoxSpider(Spider):

    name = "memeboxmm"
    allowed_domains = ["memebox.com"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 10;
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
        item_a_tags = soup.find_all(name='a', attrs={"id": re.compile(r'^name_sku_')})
        for item_a_tag in item_a_tags:
            item = CommonItem()

            item_link = item_a_tag['href']
            # item_link = 'http://cn.memebox.com/mmzq/c120140'
            m = re.match(r'(^http://cn.memebox.com/mmzq/)([\s\S]*)', item_link)
            item['id'] = m.group(2)
            item['url'] = item_link
            item['source'] = 'memebox.com'
            yield Request(item_link, callback=self.parse_memebox_item, meta={'item': item})

    def parse_memebox_item(self, response):
        """解析MeMeBox Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        pro_parameter_dic = {}

        pro_name_tag = soup.find('div', class_='product-name')
        pro_title_tag = pro_name_tag.find('span')
        # print h1_tag
        pro_parameter_dic['title'] = pro_title_tag.text

        review_tag = soup.find('a', id='goto-reviews')
        if review_tag != None:
            pro_parameter_dic['comment_count'] = filter(str.isdigit, review_tag.text.encode("utf-8"))
        # print 'ssssssssssssssss --------------- %s' % review_tag

        detail_table_tag = soup.find('table', id='product-attribute-specs-table')
        # print 'zzzzzzzzzzzzzz --------------- %s' % detail_table_tag
        detail_tbody_tag = detail_table_tag.find('tbody', recursive=False)
        detail_tr_tags = detail_tbody_tag.find_all('tr', recursive=False)

        for detail_tr_tag in detail_tr_tags:
            dic_key = Parse_Util.get_no_space_string(detail_tr_tag.find('th', class_='label').string)
            dic_value = Parse_Util.get_no_space_string(detail_tr_tag.find('td', class_='data').string)
            # PM - Oriented
            # if dic_key.strip().startswith(u'商品名称'):
            #     memebox_item['product_name'] = dic_value
            # if dic_key.strip().startswith(u'品牌'):
            #     memebox_item['brand'] = dic_value
            pro_parameter_dic[dic_key] = dic_value

        item['other_parameter'] = pro_parameter_dic

        pro_nodisplay_tag = soup.find('div', class_='no-display')
        pro_id_tag = pro_nodisplay_tag.find('input', attrs={'name': 'productId'})
        pro_id = pro_id_tag['value']
        pro_price_link = price_origin_url % str(pro_id)

        yield Request(pro_price_link, callback=self.parse_price_item, meta={'item': item})

    def parse_price_item(self, response):
        data = response.body
        data = data.decode('UTF-8')
        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        print 'sssssssssss ------------- %s' % data
        json_data = json.loads(data, 'UTF-8')
        pro_dic = json_data['data'][0]
        pro_parameter_dic['promotion_price'] = pro_dic['price']
        pro_parameter_dic['price'] = pro_dic['originPrice']

        yield item




