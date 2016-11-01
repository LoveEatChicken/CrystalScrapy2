#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
from crawler.utils.parse_util import Parse_Util

pre_list_url = 'http://search.lefeng.com/search/showresult?keyword=%E9%9D%A2%E8%86%9C&is_has_stock=0&'
suf_list_origin_url = 'page=%d&moreBrand=0'
detail_origin_url = 'http://product.lefeng.com/product/%d.html'
class LeFengSpider(Spider):

    name = "lefengmm"
    allowed_domains = ["lefeng.com"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 46;
        # MAX_PAGE_COUNT = 2;
        for page in range(1,MAX_PAGE_COUNT):
            suf_list_url = suf_list_origin_url % page
            url = pre_list_url + suf_list_url
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        #print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        pro_group_tag = soup.find('div', id='productDivGroup')
        pro_info_tags = pro_group_tag.find_all('div', class_="pruwrap", recursive=False)
        for pro_info_tag in pro_info_tags:

            item = CommonItem()
            item_id = pro_info_tag['data-pid']
            item_link = detail_origin_url % int(item_id)
            # item_link = 'http://product.lefeng.com/product/98757241.html'
            item['id'] = item_id
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            item['url'] = item_link
            item['source'] = 'lefeng.com'
            yield Request(item_link, callback=self.parse_lefeng_item, meta={'item': item})

    def parse_lefeng_item(self, reponse):
        """解析Lefeng Item"""
        data = reponse.body
        soup = BeautifulSoup(data, "html5lib")
        item = reponse.meta['item']
        pro_parameter_dic = {}

        title_div_tag = soup.find('div', class_="bigProduct-c")
        title_tag = title_div_tag.find('h1')
        title_i_tag = title_tag.find('i', recursive=False)
        if title_i_tag != None:
            title_i_tag.extract()
        pro_parameter_dic['title'] = Parse_Util.get_no_space_string(title_tag.text)
        print 'zzzzzzzzzzz------------- %s' % pro_parameter_dic

        detail_info_tag = soup.find('table', class_='detail-info-table')
        detail_tbody_tag = detail_info_tag.find('tbody', recursive=False)
        detail_tags = detail_tbody_tag.find_all('tr')
        pro_detail_parameter_dic = Parse_Util.structure_parameter_dic(detail_tags, u':')

        pro_parameter_dic = dict(pro_parameter_dic, **pro_detail_parameter_dic)

        price_c_tag = soup.find('div', class_='dity-price-c ')
        price_tag = price_c_tag.find('strong')
        origin_pirce_tag = price_c_tag.find('b', class_='marketPrice-s')

        pro_parameter_dic['price'] = origin_pirce_tag.text.strip(u'¥ ')
        pro_parameter_dic['promotion_price'] = price_tag.text

        item['other_parameter'] = pro_parameter_dic

        yield item