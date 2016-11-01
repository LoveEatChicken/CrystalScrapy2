#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
from crawler.utils.parse_util import Parse_Util
import scrapy
import re
import json

price_origin_url = 'http://www.sasa.com/product-ajax_product_price-%s.html'
seckill_price_origin_url = 'http://www.sasa.com/seckill-ajax_product_price-%s.html'
comment_origin_url = 'http://www.sasa.com/product-goodsDiscussInit-%s.html? invalid_post_data=1'
comment_origin_url2 = 'http://www.sasa.com/product-goodsDiscussInit-%s.html'
class SaSaSpider(Spider):

    name = "sasamm"
    allowed_domains = ["sasa.com"]

    def start_requests(self):
        # 最大页码
        # MAX_PAGE_COUNT = 40;
        MAX_PAGE_COUNT = 2;
        for page in range(1, MAX_PAGE_COUNT):
            page_str = str(page)
            yield scrapy.FormRequest("http://www.sasa.com/gallery-ajax_get_goods.html",
                                       formdata={'cat_id': '55', 'page': page_str},
                                       callback=self.parse)

    def parse(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        #找到所有商品item标签
        # print 'eeeeeee ----------- %s' % data
        pro_p_tags = soup.find_all(name='p', class_='des03')
        for pro_p_tag in pro_p_tags:
            suffix_item_link = pro_p_tag.find('a', recursive=False)['href']
            item = CommonItem()

            item_link = 'http://www.sasa.com' + suffix_item_link
            # item_link = '/facialcare/Dr_Morita-108132106001.html'
            m = re.match(r'(^/facialcare/)([\s\S]*)(.html)', suffix_item_link)
            item['id'] = m.group(2)
            item['url'] = item_link
            item['source'] = 'sasa.com'
            yield Request(item_link, callback=self.parse_sasa_item, meta={'item': item})

    def parse_sasa_item(self, response):
        """解析SaSa Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        pro_parameter_dic = {}

        start_end_tag = soup.find('span', class_='now_start_end_time_msg')
        if start_end_tag is not None:
            pro_title_tag = soup.find('div', class_='product-line')
            b_tag = pro_title_tag.find('b', class_='yew bonded_words_show')
            pro_info_tag = pro_title_tag.find('div', id='product_information')
            if b_tag is not None:
                b_tag.extract()
            if pro_info_tag is not None:
                pro_info_tag.extract()
            pro_title_text = Parse_Util.get_no_space_string(pro_title_tag.text)
        else:
            pro_title_tag = soup.find('div', class_='product-titles')
            b_title_tag = pro_title_tag.find('b', recursive=False)
            if b_title_tag is not None:
                b_title_tag.extract()
            pro_title_text = Parse_Util.get_no_space_string(pro_title_tag.text)
        pro_parameter_dic['title'] = pro_title_text

        pro_attributes_tag = soup.find('div', class_='product-attributes mod')
        pro_clearfix_tag = pro_attributes_tag.find('ul', class_='clearfix', recursive=False)
        pro_li_tags = pro_clearfix_tag.find_all('li', recursive=False)
        for pro_li_tag in pro_li_tags:
            pro_detail_key = Parse_Util.get_no_space_string(pro_li_tag.find('span').string.replace(u'：',''))
            pro_detail_value= Parse_Util.get_no_space_string(pro_li_tag.find('div', class_='attributes-cont').string)
            pro_parameter_dic[pro_detail_key] = pro_detail_value

        good_id = soup.find('input', attrs={'name': 'goods[goods_id]'})['value']
        pro_parameter_dic['good_id'] = good_id
        item['other_parameter'] = pro_parameter_dic

        seckill_price_tag = soup.find('input', attrs={'name': 'goods[seckill_id]'})

        if seckill_price_tag is not None:
            pro_price_link = seckill_price_origin_url % seckill_price_tag['value']
        else:
            pro_id = soup.find('input', attrs={'name': 'goods[product_id]'})['value']
            pro_price_link = price_origin_url % pro_id

        # print 'pricelink ---------------- %s' % pro_price_link
        yield Request(pro_price_link, callback=self.parse_price_item, meta={'item': item})

    def parse_price_item(self, response):
        data = response.body
        data = data.decode('UTF-8')
        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        # print 'sssssssssss ------------- %s' % data
        pro_dic = json.loads(data, 'UTF-8')

        pro_parameter_dic['promotion_price'] = pro_dic['price']
        pro_parameter_dic['price'] = pro_dic['mktprice']

        pro_comment_link = comment_origin_url % pro_parameter_dic['good_id']

        yield Request(pro_comment_link, callback=self.parse_comment_item, meta={'item': item})

    def parse_comment_item(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        print 'zzzzzzzz ------- %s' % item
        # print 'sssssssssss ------------- %s' % data
        comment_star_tag = soup.find('p', class_='koubeipoint red')

        if comment_star_tag is None:
            pro_comment_link = comment_origin_url2 % pro_parameter_dic['good_id']
            yield Request(pro_comment_link, callback=self.parse_comment2_item, meta={'item': item})
        else:
            comment_count_tag = soup.find('div', class_='title').find('i', recursive=False)
            pro_parameter_dic['comment_star'] = comment_star_tag.text
            pro_parameter_dic['comment_count'] = comment_count_tag.string
            del pro_parameter_dic['good_id']
            yield item

    def parse_comment2_item(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        # print 'zzzzzzzz ------- %s' % item
        # print 'sssssssssss ------------- %s' % data
        comment_star_tag = soup.find('p', class_='koubeipoint red')
        comment_count_tag = soup.find('div', class_='title').find('i', recursive=False)
        pro_parameter_dic['comment_star'] = comment_star_tag.text
        pro_parameter_dic['comment_count'] = comment_count_tag.string
        del pro_parameter_dic['good_id']
        yield item

