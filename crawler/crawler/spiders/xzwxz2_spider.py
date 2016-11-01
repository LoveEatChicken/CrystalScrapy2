#!/usr/bin/env python
# coding: utf-8
from des_base_spider import BaseSpider
from scrapy.http import Request
from crawler.items import CommonItem
from crawler.items import XZWXZItem
from bs4 import BeautifulSoup
import re

today_origin_url = 'http://www.xzw.com/fortune/%s/'
tomorrow_origin_url = 'http://www.xzw.com/fortune/%s/1.html'
week_origin_url = 'http://www.xzw.com/fortune/%s/2.html'
class XZWSpider(BaseSpider):

    name = "xzwxz2"
    allowed_domains = ["xzw.com"]

    def __init__(self, **kw):
        super(XZWSpider, self).__init__(**kw)

    def start_requests(self):
        # 所有星座
        CONSTELLATIONS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
        # CONSTELLATIONS = ['Aries']
        for constellatin in CONSTELLATIONS:
            url = today_origin_url % constellatin
            yield self.make_requests_from_url(url)

    def parse(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")

        item = CommonItem()
        item['source'] = self.source
        item['url'] = response.url
        item['site'] = self.site
        item['classify'] = self.classify
        item['domain'] = self.domain
        item['subclass'] = self.subclass
        item['template_id'] = self.template_id
        p = re.match(r'(http://www.xzw.com/fortune/)(\w+)(/)', response.url)
        item['id'] = p.group(2)
        xzw_item = XZWXZItem()
        xzw_item['english'] = item['id']
        xzw_item['name'] = soup.find('div', class_='c_main').find('div', class_='top', recursive=False).find('strong').string
        xzw_item['today'] = self.parse_item(response)
        item['other_parameter'] = xzw_item

        tomorrow_link = tomorrow_origin_url % item['id']
        # print 'sssssssssss ------------ %s' % tomorrow_link

        yield Request(tomorrow_link, callback=self.parse_tomorrow_item, meta={'item': item})

    def parse_tomorrow_item(self, response):
        """解析Tomorrow Item"""
        item = response.meta['item']
        xzw_item = item['other_parameter']
        xzw_item['tomorrow'] = self.parse_item(response)

        week_link = week_origin_url % item['id']

        yield Request(week_link, callback=self.parse_week_item, meta={'item': item})

    def parse_week_item(self, response):
        """解析week Item"""
        item = response.meta['item']
        xzw_item = item['other_parameter']
        xzw_item['week'] = self.parse_item(response)

        yield item

    def parse_item(self, response):
        data = response.body
        soup = BeautifulSoup(data, "html5lib")

        xz_detail_dic = {}
        main_div = soup.find('div', class_='c_main')
        dl_tag = main_div.find('dl', recursive=False)
        h4_tag = dl_tag.find('h4')
        small_tag = h4_tag.find('small')
        if small_tag is not None:
            small_tag.extract()
        xz_detail_dic['title'] = h4_tag.string
        xz_detail_dic['img'] = ''

        dd_tag = dl_tag.find('dd')
        ul_tag = dd_tag.find('ul')
        li_tags = ul_tag.find_all('li')
        # filter_key_list = [u'商谈指数：', u'短评：']
        #database_key_list = [u'整体运势：', u'健康运势：', u'幸运颜色：', u'健康指数：', u'事业学业：', u'财富运势：', u'提防星座：', u'速配星座：']
        score_key_list = [u'整体运势：', u'健康运势：', u'事业学业：', u'财富运势：', u'爱情运势：']
        fortune = {}
        for li_tag in li_tags:
            li_tag_origin_key = li_tag.find('label').string
            li_tag_key = li_tag.find('label').string.replace(u'：', '')
            if li_tag_origin_key in score_key_list:
                width = li_tag.find('em')['style']
                m = re.match(r'(width:)(\d+)(px;)', width)
                star = float(m.group(2)) / 16
                # print 'eeeeeeee --------- %.1f' % star
                dic_value = star
            else:
                dic_value = li_tag.text.strip(li_tag_origin_key)
            fortune[li_tag_key] = dic_value
        xz_detail_dic['fortune'] = fortune

        desc = {}
        c_box_div = soup.find('div', class_='c_box')
        c_cont_div = c_box_div.find('div', class_='c_cont')
        p_tags = c_cont_div.find_all('p')
        for p_tag in p_tags:
            p_key = p_tag.find('strong').string
            p_value = p_tag.find('span').string
            desc[p_key] = p_value
        xz_detail_dic['desc'] = desc

        return xz_detail_dic
