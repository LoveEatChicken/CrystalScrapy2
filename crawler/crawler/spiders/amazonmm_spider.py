#!/usr/bin/env python
# coding: utf-8
from scrapy.spiders import Spider
from scrapy.http import Request
from crawler.items import CommonItem
from crawler.items import AmazonMMItem
from bs4 import BeautifulSoup
import re

pre_list_url = 'https://www.amazon.cn/s/ref=lp_747006051_pg_2?rh=n%3A746776051%2Cn%3A%21746777051%2Cn%3A746782051%2Cn%3A747006051&'
suf_list_origin_url = 'page=%d&ie=UTF8&qid=1475916156&spIA=B00PLAIAX8,B01B403G7I,B0146NI8PA'
detail_origin_url = 'https://www.amazon.cn/dp/'
class AmazonSpider(Spider):

    name = "amazonmm"
    allowed_domains = ["amazon.cn"]

    def start_requests(self):
        # 最大页码
        MAX_PAGE_COUNT = 94;
        # MAX_PAGE_COUNT = 3;
        for page in range(1, MAX_PAGE_COUNT):
            suf_list_url = suf_list_origin_url % page
            url = pre_list_url + suf_list_url
            # url = 'https://www.amazon.cn/s/ref=lp_747006051_pg_2?rh=n%3A746776051%2Cn%3A%21746777051%2Cn%3A746782051%2Cn%3A747006051&page=2&ie=UTF8&qid=1475912114&spIA=B00PLAIAX8,B01300E1BK,B019ROTVUY'
            # print 'urllllllllllllllllllllllllllllllllll-------------------------%s' % url
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        #找到所有商品item标签
        result_tags = soup.find_all(name='li', attrs={"id": re.compile(r'^result_')})
        for li_tag in result_tags:
            # print 'li : %s ------- %s' % (li_tag['id'], li_tag)
            item_id = li_tag['data-asin']
            item = CommonItem()
            item['id'] = item_id
            # item_link = 'https://www.amazon.cn/dp/B00JE7TEES'
            item_link = detail_origin_url + item_id
            # print 'linkkkkkkkkkkkkkkkkkkkkk ----------- %s' % item_link
            item['url'] = item_link
            item['source'] = 'amazon.cn'
            yield Request(item_link, callback=self.parse_amazon_item, meta={'item': item})

    def parse_amazon_item(self, response):
        """解析Amazon Item"""
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        amazon_item = AmazonMMItem()
        # amazon_price_tag = soup.find('span', id='priceblock_ourprice')
        # print 'amazon_price ----- %s' % amazon_price_tag
        # amazon_item['price'] = amazon_price_tag.string
        title_tag = soup.find('span', id="productTitle")
        # print 'titletag -------------------- %s' % title_tag
        amazon_item['title'] = title_tag.text
        # print 'title -------- %s' % title_tag.text
        brand_tag = soup.find('a', id="brand")
        amazon_item['brand'] = brand_tag.text
        # print 'brand -------- %s' % brand_tag.text
        # goods_tag = soup.find('ul', class_='goods_parameter')
        item['other_parameter'] = amazon_item

        yield item