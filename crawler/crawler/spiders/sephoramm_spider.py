#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
from crawler.utils.parse_util import Parse_Util

list_origin_url = 'http://www.sephora.cn/category/230175-60001/page%d/'
detail_origin_url = 'http://www.sephora.cn/product/%d.html'
js_origin_url = 'http://www.sephora.cn/webapp/wcs/stores/servlet/RefreshProductDetailUp?storeId=10001&catalogId=10052&langId=-7&skuId=%d&proId=%d&categoryLevel1Name=&refresh=ajax&nowtime=1476084085345'
class SephoraSpider(Spider):

    name = "sephoramm"
    allowed_domains = ["sephora.cn"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 15;
        # MAX_PAGE_COUNT = 2;
        for page in range(1, MAX_PAGE_COUNT):
            url = list_origin_url % page
            # url = 'http://www.sephora.cn/category/230175-60001/page2/'
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        #找到所有商品item标签
        item_span_tags = soup.find_all('span', class_='quickView')
        for item_span_tag in item_span_tags:
            # print 'divvvvvvvv ------------------- %s' % item_div_tag
            item_id = item_span_tag['name']
            item = CommonItem()
            item['id'] = item_id
            item['template_id'] = 4
            item['domain'] = 'cosmetics'
            item['classify'] = 'mask'
            item['subclass'] = 'mask'
            item_link = detail_origin_url % int(item_id)
            # print 'itemlink-----------------%s' % item_link
            item['url'] = item_link
            item['source'] = 'sephora.cn'
            yield Request(item_link, callback=self.parse_sephora_item, meta={'item': item})

    def parse_sephora_item(self, response):
        """解析sephora Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        parameter_dic = {}

        pro_name_tag = soup.find('input', id='productNa')
        parameter_dic['product_name'] = pro_name_tag['value']

        pro_enName_tag = soup.find('p', id='enName')
        parameter_dic['ename'] = Parse_Util.get_no_space_string(pro_enName_tag.text)

        pro_info_tag = soup.find('div', class_='popProDet proDetInfo floatR')
        pro_title_tag = pro_info_tag.find('h1', recursive=False)
        parameter_dic['title'] = Parse_Util.get_no_space_string(pro_title_tag.text)

        brand_img_tag = soup.find('a', class_='proBrandImg')
        brand_tag = brand_img_tag.find('img')
        parameter_dic['brand'] = brand_tag['alt']

        sku_tag = soup.find('input', id='mySelCurrentSKUID')
        parameter_dic['sku_id'] = sku_tag['value']

        item['other_parameter'] = parameter_dic
        js_url = js_origin_url % (int(parameter_dic['sku_id']), int(item['id']))
        # yield item
        yield Request(js_url, callback=self.parse_js_item, meta={'item': item})

    def parse_js_item(self, response):
        """解析js Item"""
        js_data = response.body
        js_data = js_data.decode('UTF-8')
        soup = BeautifulSoup(js_data, "html5lib")
        item = response.meta['item']
        parameter_dic = item['other_parameter']

        pro_price_tag = soup.find('p', class_='proPrice')
        price_span_tag = pro_price_tag.find('span', recursive=False)
        parameter_dic['price'] = price_span_tag.text

        pro_num_tag = soup.find('p', class_='proItem')
        # print 'nooooooooooo ------------- %s' % pro_num_tag
        item_no_dic = Parse_Util.structure_parameter_dic([pro_num_tag], u'：')

        skuinfo_tag = soup.find('div', id='skuInfo')
        # print 'skuinfo_tag --------- %s' % skuinfo_tag
        other_parameter_dic = Parse_Util.make_up_dic(skuinfo_tag)

        pro_all_parameter_dic = dict(dict(parameter_dic, **other_parameter_dic), **item_no_dic)
        item['other_parameter'] = pro_all_parameter_dic

        yield item