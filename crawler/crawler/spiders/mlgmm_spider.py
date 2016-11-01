#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from bs4 import BeautifulSoup
import re

list_origin_url = 'http://www.mligo.com/goods/list?p_cid=28&c_id=35&page=%d'
detail_origin_url = 'http://www.mligo.com/goods/detail/'
class MligoSpider(Spider):

    name = "mlgmm"
    allowed_domains = ["mligo.com"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 12
        # MAX_PAGE_COUNT = 2;
        for page in range(1,MAX_PAGE_COUNT):
            url = list_origin_url % page
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        #print 'dafdfasdfsa ------------ %s' % response.url
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        div_tag = soup.find('div', attrs={'id': 'product_list'})
        ul_tag = div_tag.find('ul', attrs={'class': 'cle'})
        # print 'ultagggggggggggg ------------ %s' % ul_tag
        a_tags = ul_tag.find_all('a', class_="productitem")
        # print 'a_tags --------------- %s' % a_tags
        for a_tag in a_tags:
            item = CommonItem()
            # print 'href ------------- %s' % a_tag['href']
            m = re.match(r'(/goods/detail/)(\w+)', a_tag['href'])
            # print 'id ---------------- %s' % m.group(2)
            item_id = m.group(2)
            item_link = detail_origin_url + item_id
            item['id'] = item_id
            item['url'] = item_link
            item['source'] = 'mligo.com'
            # print 'url ------------- %s' % item['url']
            yield Request(item_link, callback=self.parse_mlg_item, meta={'item': item})

    @classmethod
    def parse_mlg_item(cls, reponse):
        """解析 mlg Item"""
        data = reponse.body
        soup = BeautifulSoup(data, "html5lib")
        item = reponse.meta['item']
        parameter_dic = {}

        title_tag = soup.find('dt', class_="product_name")
        h1_tag = title_tag.find('h1')
        parameter_dic['title'] = h1_tag.text

        tbody_tag = soup.find('tbody')
        # print 'tbody ------------- %s' % tbody_tag
        tr_tags = tbody_tag.find_all('tr')
        for i, tr_tag in enumerate(tr_tags):
            td_tags = tr_tag.find_all('td')
            item_dic_key = td_tags[0].text
            item_dic_value = td_tags[1].text
            #Oriented - PM
            # if i == 0:
            #     item['product_name'] = td_tags[1].text
            # if i == 1:
            #     item['brand'] = td_tags[1].text
            # print 'key ----- %s : value ----- %s' % (td_tags[0].text, td_tags[1].text)
            parameter_dic[item_dic_key] = item_dic_value

        item['other_parameter'] = parameter_dic

        yield item

    def delete_nbsp(self, content):
        if content:
            # remove &nbsp
            pattern = re.compile(r'&nbsp;')
            txt = pattern.sub(" ", content)
            print 'txxxxxxxxxxxxxxxxxxxxt ------------ %s' % txt
            return txt