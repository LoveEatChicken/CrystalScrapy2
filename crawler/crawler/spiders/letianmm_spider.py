#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
import re
import json
from crawler.utils.parse_util import Parse_Util
from des_base_spider import BaseSpider

list_origin_url = 'http://china.lottedfs.com/handler/Category-Main?categoryId=500011000110008&pageNo=%d'
detail_origin_url = 'http://china.lottedfs.com/handler/ProductDetail-Start?productId=%s&viewCategoryId=500011000110008&tracking='
price_origin_url = 'http://rb-rec-api-apne1.recobell.io/rec/a003?callback=jQuery164042777373595163226_1476946963032&format=jsonp&cuid=f55918ce-df00-4cdd-b55a-ce246cbcbddc&device=pc&size=40&cpt=m002&iids=%s&maxp=&_=1476946965391'
class LeTianSpider(BaseSpider):

    name = "letianmm"
    allowed_domains = ["lottedfs.com", "recobell.io"]



    def __init__(self, **kw):
        super(LeTianSpider, self).__init__(**kw)
    # def start_requests(self):
    #     # 最大页码
    #
    #     url = 'http://china.lottedfs.com/handler/Category-Main?categoryId=500011000110008&pageNo=1'
    #     yield self.make_requests_from_url(url)
    #
    # def parse(self, response):
    #
    #     item = CommonItem()
    #     item_id = '10002267416'
    #     item_link = detail_origin_url % item_id
    #     item['id'] = item_id
    #     print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
    #     item['url'] = item_link
    #     item['source'] = 'lottedfs.com'
    #     yield Request(item_link, callback=self.parse_letian_item, meta={'item': item}, dont_filter=True)

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 11; #11
        # MAX_PAGE_COUNT = 2;
        for page in range(1, MAX_PAGE_COUNT):
            url = list_origin_url % page
            # url = 'http://category.dangdang.com/pg2-cid4009711.html'
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        #print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        pro_group_tag = soup.find('div', class_='cate_reco cate_reco_btmLine')
        pro_info_tags = pro_group_tag.find_all('a', onfocus="blur();")
        # print 'sssssssssssssss ------------ %s' % pro_info_tags
        for pro_info_tag in pro_info_tags:
            item = CommonItem()
            pro_href = pro_info_tag['href']
            # print 'sssssssssssssss ------------ %s' % pro_href
            m = re.match(r"(javascript:BI.goProductDetail\(\")([\s\S]*)(\", \"[\d]+\", \"\", \"\"\);)", pro_href)
            # print 'oooooooooooooo ------------ %s' % m.group(2)
            item_id = m.group(2)
            item_link = detail_origin_url % item_id
            item['source'] = self.source
            item['site'] = self.site
            item['classify'] = self.classify
            item['domain'] = self.domain
            item['subclass'] = self.subclass
            item['template_id'] = self.template_id

            item['id'] = item_id
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            item['url'] = item_link
            yield Request(item_link, callback=self.parse_letian_item, meta={'item': item})

    def parse_letian_item(self, response):
        """解析LeTian Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        pro_parameter_dic = {}

        wrap_tag = soup.find('div', id='wrap')
        script_tags = wrap_tag.find_all('script', type='text/javascript')
        pro_script_text = Parse_Util.get_no_space_string(script_tags[21].text)
        # for k, script_tag in enumerate(script_tags):
        #     print 'k : %d ------------------- %s' % (k, script_tag)
        re_brand_object = re.search(r'brandNmTemp = \'([\s\S]*)\'; brandNmTemp', pro_script_text)
        # print 'branddddddddddd1 --------------- %s' % re_brand_object.group(1)
        pro_parameter_dic['brand'] = re_brand_object.group(1)
        pro_title_tag = soup.find('meta', property='rb:itemName')
        # print 'tititititiitit ------------- %s' % pro_title_tag
        pro_parameter_dic['title'] = pro_title_tag['content']
        pro_table_tag = soup.find('table', summary=u'产品详细信息')
        pro_tbody_tag = pro_table_tag.find('tbody')
        pro_info_tags = pro_tbody_tag.find_all('tr', recursive=False)

        for pro_info_tag in pro_info_tags:
            dic_key = pro_info_tag.find('th').string
            dic_value = Parse_Util.get_no_space_string(pro_info_tag.find('td').text)
            pro_parameter_dic[dic_key] = dic_value

        pro_parameter_dic['comment_count'] = soup.find('div', id='tabmenuT').string.replace(u'条', '')
        help_tag = soup.find('div', class_='help')
        dl_tag = help_tag.find('dl', recursive=False)

        t01_num_key = dl_tag.find('dt', class_='t01').find('img')['alt']
        t01_num_value = dl_tag.find('dd', class_='r01').string
        pro_parameter_dic[t01_num_key] = t01_num_value

        t02_num_key = dl_tag.find('dt', class_='t02').find('img')['alt']
        t02_num_value = dl_tag.find('dd', class_='r02').string
        pro_parameter_dic[t02_num_key] = t02_num_value

        item['other_parameter'] = pro_parameter_dic

        pro_price_link = price_origin_url % item['id']
        # print 'priceeeeeeeeeeeeee ---------------- %s' % pro_price_link

        yield Request(pro_price_link, callback=self.parse_price_item, meta={'item': item})

    def parse_price_item(self, response):
        """解析LeTianPrice Item"""
        data = response.body
        data = data.decode('UTF-8')
        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        re_jequery = re.match(r'jQuery164042777373595163226_1476946963032\(([\s\S]*)(\);)', data)
        # print 'sssssssssss ------------- %s' % re_jequery.group(1)
        json_data = json.loads(re_jequery.group(1), 'UTF-8')
        pro_dic = json_data['products'][0]
        pro_parameter_dic['promotion_price'] = '$' + str(pro_dic['salePrice'])
        pro_parameter_dic['price'] = '$' + str(pro_dic['originalPrice'])

        yield item