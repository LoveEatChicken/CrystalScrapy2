#!/usr/bin/env python
# coding: utf-8

from scrapy import FormRequest
from scrapy.spiders import Spider
from crawler.items import CommonItem
from bs4 import BeautifulSoup
from crawler.utils.parse_util import Parse_Util
import string
import json
import re

list_origin_url = 'https://list.tmall.com/search_product.htm?spm=a220m.1000858.0.0.di0tF1&cat=50029231&s=%d&sort=s&style=g&active=1&industryCatId=50029231&type=pc#J_Filter'
detail_origin_url = 'https://detail.tmall.com/item.htm?spm=a220m.1000858.1000725.84.9fLRUJ&id=%s&areaId=110100&user_id=652154536&cat_id=50029231&is_b=1&rn=ca52d0b6536e1f57c3cf10345ed326a8'
price_origin_url = 'https://mdskip.taobao.com/core/initItemDetail.htm?itemId=%s&isAreaSell=false&household=false&sellerPreview=false&cartEnable=true&isForbidBuyItem=false&tmallBuySupport=true&tryBeforeBuy=false&cachedTimestamp=1477453800721&showShopProm=false&offlineShop=false&isRegionLevel=false&service3C=false&addressLevel=2&isSecKill=false&isPurchaseMallPage=false&queryMemberRight=true&isApparel=false&isUseInventoryCenter=false&callback=setMdskip&timestamp=1477453942958'
price_suffix_url = '&isg=Am5uvsbYbmWXp3rg2LXScXSdPs4wzTOl&isg2=AkJCOXoQrg0A8b2ZClP-8lvik07WHUYtFMoqQ4xbzLSs3-JZdKOWPchd-WxZ&areaId=110100&cat_id=50029231&ref=https%3A%2F%2Flogin.tmall.com%2F%3Fspm%3Da220o.1000855.a2226mz.2.qBfsfF%26redirectURL%3Dhttps%253A%252F%252Fdetail.tmall.com%252Fitem.htm%253Fspm%253Da220m.1000858.1000725.262.AEbVEY%2526id%253D529735026441%2526areaId%253D110100%2526user_id%253D2695140764%2526cat_id%253D50029231%2526is_b%253D1%2526rn%253D24b379e1c096bb43fd778f2809acb16d'
comment_origin_url = 'https://dsr-rate.tmall.com/list_dsr_info.htm?itemId=%s&spuId=562550482&sellerId=368609005&_ksTS=1477389148848_189&callback=jsonp190'
cookies = {
            '_cc_': 'WqG3DMC9EA%3D%3D',
            '_l_g_': 'Ug%3D%3D',
            '_med': 'dw:1440&dh:900&pw:2880&ph:1800&ist:0',
            '_nk_': 'ycz0423',
            '_tb_token_': 'LOL43jg2ylw5',
            'ck1': '',
            'cna': 'sUDpDuLY3TQCAXLxt8q7ZVd5',
            'cookie1': 'U7lVBi%2FL3GF2FfaexLTDzM9jiESgJstYhUCXyiMwzuw%3D',
            'cookie17': 'VynIBFChRMKF',
            'cookie2': '173e6a4f47779da3d6315723f891653e',
            'existShop': 'MTQ3NzQ3MTQ2OQ%3D%3D',
            'cq': 'ccp%3D0',
            'hng': '',
            'isg': 'AtracZl6VsVsEtWhwQ-N8CayK4bjPF7lPFLCm-RT1G0XV3mRwJuu9aDlUZSx',
            'l': 'AnJypuclmMC43vZsfKkWBSzSQrJUUXay',
            'linezing_session': 'lKUJ4Lc3VBHQXzeV5IfviF8I_1477450940285nkpS_1',
            'miid': '66444665845552660',
            'mt': 'np=',
            'sg': '30b',
            'lgc': 'ycz0423',
            'login': 'true',
            'pnm_cku822': '201UW5TcyMNYQwiAiwZTXFIdUh1SHJOe0BuOG4%3D%7CUm5OcktxS3JJfUV4Q31Hfig%3D%7CU2xMHDJ7G2AHYg8hAS8WLAIiDEsiSWcxZw%3D%3D%7CVGhXd1llXGZcZV5qUm9UalBpXmNBfUB5Q3dMdUB%2BS3FFcUx5TXJcCg%3D%3D%7CVWldfS0RMQ02CSkWNhg8FzlvOQ%3D%3D%7CVmhIGCcZOQQkGCEYJQU9CDMHJxsiGyYGMg8yEi4XLhMzBjgFUwU%3D%7CV25Tbk5zU2xMcEl1VWtTaUlwJg%3D%3D',
            'res': 'scroll%3A1440*5869-client%3A1440*150-offset%3A1440*5869-screen%3A1440*900',
            'skt': '606d33860edcf7ec',
            't': '2a3b00ad23be8e5fa85c97ea7674e035',
            'tg': '0',
            'thw': 'cn',
            'tk_trace': 'oTRxOWSBNwn9dPyscxqAz9fIO73QQFhF7kVkgTL59JVC7kpHTxat6tLGFTB1Ee398YXFDzN0tYDAEZWc2vyrw0lqTxpI3hrmZgRoGLr7HA%2Fbek87ThmISVEESdi%2FqG2wV3j5o4D1dIWjp5P8650I6FHzPP28w%2Fvijx%2B%2BCYRrcwWSu6tPA8VB%2BR9747rBfqrWjCL8HAX2IpMM2JBuslZZ%2FVX2CTTwud%2B1XezU%2F9EW2vs66gwI3r5zvMfLZ7CQPmJdetVl4aFUcKxEU%2FJkwQePxkKTz%2FIoeFbf%2BRDnvBay8Ef%2B1LL4r4LSOYVMScskGhifABIUrrG6nCJUHjp2EBbX2G6q2uZOsJtwKw%3D%3D',
            'tracknick': 'ycz0423',
            'tt': 'login.tmall.com',
            'uc1': 'cookie14=UoWwI9kpysNEdA%3D%3D&lng=zh_CN&cookie16=VFC%2FuZ9az08KUQ56dCrZDlbNdA%3D%3D&existShop=false&cookie21=UIHiLt3xTIkz&tag=2&cookie15=U%2BGCWk%2F75gdr5Q%3D%3D&pas=0',
            'uc3': 'sg2=AVH2U9WmPr03Hm0Dj%2B38aBi56cAJp%2BXTtvrKyl5LCpY%3D&nk2=Ggj8IsHHAw%3D%3D&id2=VynIBFChRMKF&vt3=F8dARHKtW%2FKFB97NwMA%3D&lg2=UIHiLt3xD8xYTw%3D%3D',
            'unb': '451851050',
            'uss': 'UonYuHVi18YyPNZwxjf9O6Q1JoQXP7c54ubLxOyK1OeDmHcJoLdH1qoeyhQ%3D',
            'v': '0',
        }
headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36'
        }
class TMALLMMSpider(Spider):

    name = "tmallmm"
    allowed_domains = ["tmall.com", "taobao.com"]

    def start_requests(self):
        # 最大页码
        # MAX_PAGE_COUNT = 64;
        MAX_PAGE_COUNT = 1;
        for page in range(0, MAX_PAGE_COUNT):
            url = list_origin_url % (page * 60)
            yield FormRequest(url, meta={'cookiejar': str(page)},
                              headers=headers,
                              cookies=cookies,
                              callback=self.parse)

    def parse(self, response):
        # print 'listtttttttttttttttttttttttttttttt'
        data = response.body
        # print 'data ----------------- %s' % data
        soup = BeautifulSoup(data, "html5lib")
        # 找到所有的商品代码模块
        pro_list_tag = soup.find('div', id='J_ItemList')
        # print 'listtagggg -------------------- %s' % pro_list_tag
        pro_div_tags = pro_list_tag.find_all('div', class_="product ", recursive=False)
        # print 'tagsssssss -------------------- %s' % pro_div_tags

        item_link = 'https://detail.tmall.com/item.htm?spm=a220m.1000858.1000725.84.9fLRUJ&id=36513592722&areaId=110100&user_id=652154536&cat_id=50029231&is_b=1&rn=ca52d0b6536e1f57c3cf10345ed326a8'
        yield FormRequest(item_link,
                          meta={'item_id': '36513592722'},
                          headers=headers,
                          cookies=cookies,
                          callback=self.parse_tmall_item)

        # for pro_div_tag in pro_div_tags:
        #     # print 'ppppptag ----- %s ' % (pro_div_tag)
        #     item_id = pro_div_tag['data-id']
        #     item_link = detail_origin_url % item_id
        #
        #     # yield item
        #     # print 'detaillinkkkkkkkkkkk ------------- %s' % item_link
        #     yield FormRequest(item_link,
        #                       meta={'item_id': item_id},
        #                       headers=headers,
        #                       cookies=cookies,
        #                       callback=self.parse_tmall_item)


    def parse_tmall_item(self, response):
        # print 'detailllllllllllllllllllllllllllllllllllllll'
        """解析tmall Item"""
        item_id = response.meta['item_id']
        price_prefix_link = price_origin_url % item_id
        price_link = price_prefix_link + price_suffix_url

        yield FormRequest(price_link,
                          meta={'item_id': '36513592722'},
                          headers=headers,
                          cookies=cookies,
                          callback=self.parse_price_item)

    def parse_price_item(self, response):
        item_id = response.meta['item_id']
        origin_data = response.body
        decode_data = Parse_Util.get_no_space_string(origin_data.decode('GBK'))
        # print 'zzdzzzzzzz  ----------------- %s' % decode_data
        m = re.match(r'((setMdskip \()([\s\S]*)\))', decode_data)
        # print '33333333333 ------------- %s' % m.group(3)
        py_obj = json.loads(m.group(3))
        price_info_dic = py_obj['defaultModel']['itemPriceResultDO']['priceInfo']
        price_sell_count_dic = py_obj['defaultModel']['sellCountDO']
        # print 'prceinfodic ----------- %s' % price_info_dic.keys()
        sku_ids = price_info_dic.keys()
        for sku_id in sku_ids:
            item = CommonItem()
            # print 'sku dic ------------- %s' % sku_id
            pro_parameter_dic = {}
            pro_parameter_dic['item_id'] = item_id
            pro_parameter_dic[u'月销量'] = price_sell_count_dic['sellCount']
            item['source'] = 'tmall.com'
            item['domain'] = 'cosmetics'
            item['classify'] = 'mask'
            item['subclass'] = 'mask'
            item['id'] = sku_id
            sku_dic = price_info_dic[sku_id]
            pro_parameter_dic['price'] = sku_dic['price']


            if sku_dic.has_key('promotionList'):
                promotion_price_dic = sku_dic['promotionList'][0]
                pro_parameter_dic['promotion_price'] = promotion_price_dic['price']

            if sku_id == 'def':
                item['id'] = item_id

            sku_parameter = "&skuId=%s" % sku_id
            sku_detail_url = detail_origin_url % item_id
            sku_link = sku_detail_url + sku_parameter
            item['url'] = sku_link

            item['other_parameter'] = pro_parameter_dic
            yield FormRequest(sku_link, meta={'item': item},
                              headers=headers,
                              cookies=cookies,
                              callback=self.parse_detail_item)


    def parse_detail_item(self, response):
        # print 'detail ---------- %s' % response.url
        data = response.body
        soup = BeautifulSoup(data, "html5lib")
        item = response.meta['item']
        sku_id = item['id']
        pro_parameter_dic = item['other_parameter']
        pro_title_tag = soup.find('div', class_='tb-detail-hd').find('h1', recursive=False)
        pro_parameter_dic['title'] = Parse_Util.get_no_space_string(pro_title_tag.string)

        pro_detail_tags = soup.find('ul', id='J_AttrUL').find_all('li')
        for pro_detail_tag in pro_detail_tags:
            detail_no_space_text = Parse_Util.get_no_space_string(pro_detail_tag.text)
            # print 'no space text ------------ %s' % detail_no_space_text
            if string.find(detail_no_space_text, u"：") != -1:
                pro_dic_array = detail_no_space_text.split(u"：")
            if string.find(detail_no_space_text, u':') != -1:
                pro_dic_array = detail_no_space_text.split(u':')
            # print 'araaaaa ------------- %s' % pro_dic_array
            pro_parameter_dic[pro_dic_array[0]] = pro_detail_tag['title']

        J_DetailMeta_tag = soup.find('div', id='J_DetailMeta')
        tm_clear_tag = J_DetailMeta_tag.find('div', class_='tm-clear', recursive=False)
        sku_script_tag = tm_clear_tag.find_all('script')[-1]
        # print 'sku ------------- %s' % sku_script_tag
        m = re.search(r'[\s\S]*TShop.Setup\(([\s\S]*)( \); }\)\(\);)',
                      Parse_Util.get_no_space_string(sku_script_tag.text))
        # print 'sku dic1 ---------------- %s' % m.group(1)
        sku_dic = json.loads(m.group(1))
        if sku_dic.has_key('valItemInfo'):
            item_info = sku_dic['valItemInfo']
            sku_map = item_info['skuMap']
            sku_list = item_info['skuList']
            print 'sku-list ---------- %s' % sku_list
            for sku_dic in sku_list:
                # print 'skuuuuuuuuuuuuuuuuuid ---------------- %s' % sku_dic
                if sku_dic['skuId'] == sku_id:
                    pro_parameter_dic['specification'] = sku_dic['names']
                    pro_parameter_dic['pvs'] = sku_dic['pvs']
                    pvs_key = ';%s;' % sku_dic['pvs']
                    pro_parameter_dic['price'] = sku_map[pvs_key]['price']
                    pro_parameter_dic['stock'] = sku_map[pvs_key]['stock']

        else:
            print 'item stock specification null'

        comment_url = comment_origin_url % pro_parameter_dic['item_id']

        yield FormRequest(comment_url, meta={'item': item},
                              headers=headers,
                              cookies=cookies,
                              callback=self.parse_comment_item)

    def parse_comment_item(self, response):
        print 'comment ---------- %s' % response.body
        item = response.meta['item']
        pro_parameter_dic = item['other_parameter']
        decode_data = response.body.decode('utf-8')
        m = re.match(r'([jsonp0-9]+\()([\s\S]*)(\))', decode_data)
        comment_obj = json.loads(m.group(2))
        pro_parameter_dic['gradeAvg'] = comment_obj['dsr']['gradeAvg']
        pro_parameter_dic[u'累计评价'] = comment_obj['dsr']['rateTotal']

        yield item
















