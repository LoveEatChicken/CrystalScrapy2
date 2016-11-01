# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item,Field

class CommonItem(Item):
    """DataBase-Oriented"""
    url = Field();
    #详情页host
    source = Field();
    id = Field();
    #站点名
    site = Field();
    # 站点名
    template_id = Field();
    #全局唯一ID,source+id拼接
    uuid = Field();
    exception_code = Field();
    exception = Field();
    other_parameter = Field();
    domain = Field()
    classify = Field()
    subclass= Field()

class JDMMItem(Item):
    #归一化字典
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();
    price = Field();

    # 全部评价数
    comment_count = Field();
    # 好评数
    good_count = Field();
    # 中评数
    general_count = Field();
    # 差评数
    bad_count = Field();
    # 好评度
    good_rate = Field();


class TMALLMMItem(Item):

    id = Field();
    source = Field();
    title = Field();
    url = Field();
    price = Field();
    brand = Field();
    name = Field();
    #适用肤质
    skin = Field();
    function = Field();
    type = Field();
    sex = Field();
    #净含量/面贴膜数量
    net_content = Field();
    #产地
    origin = Field();
    #全部评价数
    evaluate_count = Field();
    #好评数
    praise_count = Field();
    #中评数
    assessment_count = Field();
    #差评数
    bad_review_count = Field();

class YHDMMItem(Item):

    source = Field();
    id = Field();
    title = Field();
    brand = Field();
    url = Field();
    #产品产地
    product_origin = Field();
    product_name = Field();
    #产品名称(全球购)
    function = Field();
    #分类
    category = Field();
    #货号
    item_no = Field();
    #适用皮肤
    for_skin = Field();
    #类型
    type = Field();
    sex = Field();
    jd_price = Field();
    price = Field();
    #商品产地
    goods_origin = Field();
    mask_num = Field();
    #商品编号
    goods_no = Field();
    #商品毛重
    goods_gross_weight = Field();
    #全部评价数
    evaluate_count = Field();
    #好评数
    praise_count = Field();
    #中评数
    assessment_count = Field();
    #差评数
    bad_review_count = Field();
    #好评度
    praise_rating = Field();

class KaoLaMMItem(Item):
    #详情列表
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();
    price = Field();
    reference_price = Field();
    praise_rating = Field();
    # 全部评价数
    evaluate_count = Field();
    #晒单数
    public_order_count = Field();

class MLGMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

class SuningMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

class AmazonMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

    price = Field();
    # 优惠价
    preferential_price = Field();
    # 全部评价数
    evaluate_count = Field();
    # 好评度
    praise_rating = Field();

class DangDangMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

    price = Field();
    # 优惠价
    origin_price = Field();
    # 全部评价数
    evaluate_count = Field();
    # 好评度
    praise_rating = Field();

class SephoraMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

    price = Field();
    #货号
    item_no = Field();
    sku_id = Field();

class StrawberryMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

    price = Field();
    #货号
    item_no = Field();
    sku_id = Field();

class LeFengMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

    price = Field();
    origin_price = Field();

class LiZiMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

    price = Field();
    ping_star = Field();

class MeMeBoxMMItem(Item):
    good_detail = Field();

    title = Field();
    product_name = Field();
    brand = Field();

    price = Field();
    origin_price = Field();
    comment_count = Field();


class XZWXZItem(Item):

    name = Field()
    english = Field()
    img = Field()
    today = Field()
    tomorrow = Field()
    week = Field()





