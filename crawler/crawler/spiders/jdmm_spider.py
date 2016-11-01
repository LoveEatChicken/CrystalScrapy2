#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from crawler.items import JDMMItem
from crawler.utils.parse_util import Parse_Util
from bs4 import BeautifulSoup
import json
import re
import string

comment_origin_url = 'https://club.jd.com/productpage/p-%d-s-0-t-1-p-0.html?callback=jQuery8978272&_=1474255680720'
price_origin_url = 'http://p.3.cn/prices/mgets?type=1&area=1_72_2799_0&pdtk=&pduid=1156202628&pdpin=&pdbp=0&skuIds=J_%d&callback=jQuery1555758&_=1474543054760'

class JDMMSpider(Spider):

    name = "jdmm"
    allowed_domains = ["jd.com","jd.hk","p.3.cn"]

    def start_requests(self):
        # 最大页码
        # MAX_PAGE_COUNT = 260;
        MAX_PAGE_COUNT = 2;
        for page in range(1,MAX_PAGE_COUNT):
            url = 'http://list.jd.com/list.html?cat=1316,1381,1392&page=%d&trans=1&JL=6_0_0#J_main' % page
            yield self.make_requests_from_url(url)


    # def start_requests(self):
    #     id = '1938451'
    #     item = CommonItem()
    #     item['id'] = id
    #     item_link = 'https://item.jd.hk/%s.html' % id
    #     # item_link = 'http://item.jd.com/1622962.html'
    #     item['url'] = item_link
    #     item['source'] = Parse_Util.get_source_origin(item_link)
    #     yield Request(item_link, callback=self.parse_word_wide_item, meta={'item': item, 'id': id})

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
            item = CommonItem()
            item['id'] = id
            item['template_id'] = 1
            item['domain'] = 'cosmetics'
            item['classify'] = 'mask'
            item['subclass'] = 'mask'
            # is_word_wide = True
            if is_word_wide:
                item_link = 'https://item.jd.hk/%s.html' % id
                # item_link = 'https://item.jd.hk/1938316.html'
                item['url'] = item_link
                item['source'] = 'jd.hk'
                yield Request(item_link, callback=self.parse_word_wide_item, meta={'item': item, 'id': id})
            else:
                item_link = 'http://item.jd.com/%s.html' % id
                # item_link = 'http://item.jd.com/10318794238.html'
                item['url'] = item_link
                item['source'] = 'jd.com'
                yield Request(item_link, callback=self.parse_jd_item, meta={'item': item, 'id': id})

    # def delete_node_content(self, parentControl, node):
    #     modified_value = parentControl.text
    #
    #     del_node = parentControl.find(node)
    #     # print 'delnode --------------- %s' % del_node
    #     if del_node == None:
    #         modified_value = parentControl.text
    #     else:
    #         modified_value = parentControl.text.strip(del_node.string)
    #
    #     return modified_value

    def delete_node_content(self, parentControl, node):
        modified_value = ''
        del_node = parentControl.find(node)
        del_node.decompose()
        for string in parentControl.stripped_strings:
            modified_value = modified_value+string.strip()
        return modified_value


    def parse_jd_item(self, response):
        """解析普通jd Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        item_id = response.meta['id']

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
        jd_item = JDMMItem()
        jd_item['title'] = title.encode('utf-8')

        good_tag = soup.find('ul', attrs={'id': 'parameter2'})
        jd_item['product_name'] = Parse_Util.get_parse_value(good_tag, u'商品名称：')
        jd_item['good_detail'] = Parse_Util.make_up_dic(good_tag)

        ul_tag = soup.find('ul', id="parameter-brand")
        # print 'ul_tag -------------- %s' % ul_tag
        jd_item['brand'] = 'None'
        if ul_tag != None:
            jd_item['brand'] = ul_tag.find('li').get("title")
            li_tags = ul_tag.find_all('li')
            li_tag = li_tags[0]

            p = re.compile('\s+')
            brand_str = re.sub(p, '', li_tag.text)
            if string.find(brand_str, u'♥') != -1:
                list_str = brand_str.split(u'♥')
                brand_str = list_str[0]
            brand_str_list = brand_str.split(u'：')
            # print 'brand_str_list --------- %s' % brand_str_list
            jd_item['good_detail'][brand_str_list[0]] = brand_str_list[1]

        item['other_parameter'] = jd_item

        item_comment_link = comment_origin_url % (int(item_id))
        yield Request(item_comment_link, callback=self.parse_comment_detail, meta={'item': item})

    def parse_word_wide_item(self,response):
        """解析全球购ITEM"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        item_id = response.meta['id']

        title_tag = soup.find('div', id="name")

        jd_item = JDMMItem()
        jd_item['title'] = self.delete_node_content(title_tag, 'span')

        good_tag = soup.find('ul', id="parameter2")
        jd_item['product_name'] = Parse_Util.get_parse_value(good_tag, u'商品名称：')
        jd_item['brand'] = Parse_Util.get_parse_value(good_tag, u'品牌：')
        jd_item['good_detail'] = Parse_Util.make_up_dic(good_tag)
        item['other_parameter'] = jd_item

        item_comment_link = comment_origin_url % (int(item_id))
        yield Request(item_comment_link, callback=self.parse_comment_detail, meta={'item': item})

    def parse_comment_detail(self, response):
        """解析评价"""
        jquery_data = response.body
        jquery_data = jquery_data.decode('GBK')
        item = response.meta['item']
        jd_item = item['other_parameter']

        json_data = Parse_Util.get_json_str(jquery_data)

        data = json.loads(json_data, 'UTF-8')
        jd_item['comment_count'] = data['productCommentSummary']['commentCount']
        jd_item['good_count'] = data['productCommentSummary']['goodCount']
        jd_item['general_count'] = data['productCommentSummary']['generalCount']
        jd_item['bad_count'] = data['productCommentSummary']['score1Count']
        jd_item['good_rate'] = data['productCommentSummary']['goodRate']

        item_price_link = price_origin_url % (int(item['id']))
        # print 'item_price_link ------------ %s' % item_price_link
        yield Request(item_price_link, callback=self.parser_price_detail, meta={'item': item})

    def parser_price_detail(self, response):
        """解析价格"""
        jquery_data = response.body
        jquery_data = jquery_data.decode('UTF-8')
        item = response.meta['item']
        jd_item = item['other_parameter']

        json_data = Parse_Util.get_json_str(jquery_data)

        data = json.loads(json_data, 'UTF-8')
        jd_item['price'] = data[0]['p']

        yield item
