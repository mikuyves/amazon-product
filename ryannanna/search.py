# coding=utf-8
import re
import json
import pprint
import random
import time
from urllib.error import HTTPError
from lxml import html
import requests
from amazon.api import AmazonAPI
import bottlenose.api

import bottlenose
from bs4 import BeautifulSoup
from amazon_scraper import AmazonScraper
import leancloud
from fake_useragent import UserAgent

from secret import AMZ_ACCESS_KEY, AMZ_SECRET_KEY, AMZ_ASSOC_TAG,\
    AMZ_ACCESS_KEY2, AMZ_SECRET_KEY2, AMZ_ASSOC_TAG2, AMZ_COOKIE,\
    LC_APP_ID, LC_APP_KEY, LC_USERNAME, LC_PASSWORD


# Leancloud
# 初始化 Leancloud 应用。
leancloud.init(LC_APP_ID, LC_APP_KEY)

# 登陆 Leancloud 应用。
user = leancloud.User()
user.login(LC_USERNAME, LC_PASSWORD)

ua = UserAgent()


# AMAZON
# 处理 amazon api 经常性的 503 错误。
def error_handler(err):
    ex = err['exception']
    if isinstance(ex, HTTPError) and ex.code == 503:
        time.sleep(random.expovariate(0.1))
        return True

# Amazon api 验证资料。
AUTH_ARGS = [AMZ_ACCESS_KEY, AMZ_SECRET_KEY, AMZ_ASSOC_TAG]
# Amazon api 请求设置。
AUTH_KWARGS = {
    'Region': 'CN',
    'MaxQPS': 0.9,
    'Timeout': 5.0,
    'ErrorHandler': error_handler}

amz_product = AmazonAPI(*AUTH_ARGS, **AUTH_KWARGS)

amz_scraper = AmazonScraper(*AUTH_ARGS, **AUTH_KWARGS)

amz_nose = bottlenose.Amazon(
    Parser=lambda text: BeautifulSoup(text, 'xml'),
    *AUTH_ARGS,
    **AUTH_KWARGS)


class AmazonLookupItem(object):
    # Wrap all the useful api from AmazonAPI and add some new.
    def __init__(self, asin):
        amz = AmazonAPI(*AUTH_ARGS, **AUTH_KWARGS)
        print('\n>>> Parsing item %s from api...' % asin)
        self.item_api = amz.lookup(ItemId=asin)
        print('Done.\n')

    @property
    def is_prime(self):
        return self.item_api._safe_get_element_text('Offers.Offer.OfferListing.IsEligibleForPrime')

    @property
    def store_id(self):
        return self.item_api._safe_get_element_text('SellerListing.Seller.StoreId')

    @property
    def store_name(self):
        return self.item_api._safe_get_element_text('SellerListing.Seller.StoreName')

    @property
    def title(self):
        return self.item_api.title

    @property
    def brand(self):
        return self.item_api.brand

    @property
    def price(self):
        if self.item_api.price_and_currency:
            return float(self.item_api.price_and_currency[0])
        else:
            return None

    @property
    def color(self):
        return self.item_api._safe_get_element_text('ItemAttributes.Color')

    @property
    def features(self):
        return self.item_api.features

    def get_detail(self, doc):
        # doc: response page html to doc.
        raw_details = doc.xpath('//span[@class="a-list-item"]/text()')
        return ' '.join(''.join(raw_details).split()) if raw_details else None

    @property
    def detail_page_url(self):
        return self.item_api.detail_page_url

    @property
    def small_pic(self):
        return self.item_api.small_image_url

    @property
    def medium_pic(self):
        return self.item_api.medium_image_url

    @property
    def large_pic(self):
        return self.item_api.large_image_url

    # 弃用，不准确。
    # @property
    # def availability(self):
    #     return self.item_api.availability

    # 弃用,没有返回数据。
    # @property
    # def size(self):
    #     return self.item_api.get_attributes('ClothingSize')


class AmzProduct(object):
    def __init__(self, url):
        # 处理基本信息： url 和 asin。
        self.raw_url = url
        self.item_id = self.url2id(url)
        self.url = self.id2url(self.item_id)

        # 抓取网页源代码内容。
        print('\n>>> Parsing item URL...')
        self.response, self.page_doc = get_html_doc(self.url)

        # 通过 amazon api 获取 asin=item_id 的商品信息。可能是 prod 的 spu 或 其中一个 sku。
        print('\n>>> Getting info from Amazon api...')
        self.item_api = AmazonLookupItem(self.item_id)

        # 生成 spu 和 sku。
        print('\n>>> Initializing SPU and SKU...')
        self.spu, self.sku_list = self.init_spu_and_sku()

        # 获取所有 SKU 和 SPU 的详细数据。注意顺序，首先分析 SKU。
        self.parse_sku_list()
        self.parse_spu()
        self.parse_hires_pic_urls()
        self.lc_save()

    def __str__(self):
        if self.spu.get('name'):
            return self.spu['name']
        else:
            return self.item_id

    def url2id(self, url):
        url_re = re.compile(r'/(dp|gp/product)/(\S{,10})/(ref)?')
        return url_re.search(url).group(2)

    def id2url(self, id):
        return 'https://www.amazon.cn/dp/{id}/'.format(id=id)

    def init_spu_and_sku(self):
        # pattern = re.compile(r"var dataToReturn = ({((\n|.)*)});", re.MULTILINE)
        # 产品 SPU 及 SKU 数据的 scirpt 标签内容。
        scripts= [s for s in self.page_doc.xpath('//script/text()') if 'dataToReturn' in s]
        if scripts:
            script = scripts[0]

            # 处理 SPU。
            spu_re = re.compile(r'"parentAsin" : "(.*)"')
            spu_asin = spu_re.search(script).group(1)
            spu = {'asin': spu_asin}

            # 处理 SKU。
            # SKU 数据格式：
            # key: asin  :  value: [尺寸1， 尺寸2， 颜色]
            # B01IJWFCQC [u'Baby', u'9 \u4e2a\u6708', u'Best Day Evert']
            sku_re = re.compile(r'"dimensionValuesDisplayData" : (.*),')
            sku_raw_data = sku_re.search(script).group(1)
            sku_dict = json.loads(sku_raw_data)

            sku_list = []
            for asin, names in sku_dict.items():
                sku = {
                    'asin': asin,
                    'name': '-'.join(names),
                    'url': self.id2url(asin)
                }
                try:
                    sku['special_size'] = names[-3]
                except IndexError:
                    print('This SKU has not special size.')
                try:
                    sku['size'] = names[-2]
                except IndexError:
                    print('This SKU has not size.')
                try:
                    sku['color'] = names[-1]
                except IndexError:
                    print('This SKU has not color.')

                sku_list.append(sku)

        else:
            print('This product has no SKU.')
            spu = {
                'asin': self.item_id,
            }
            sku_list = [spu]

        print('======> Got SPU and SKU.')
        pprint.pprint(spu)
        pprint.pprint(sku_list)
        return [spu, sku_list]

    def parse_sku_list(self):
        print('\n>>> Parsing SKU list...')
        for sku in self.sku_list:
            sku_asin = sku.get('asin')
            if sku_asin:
                # 请求。
                item = AmazonLookupItem(sku_asin)
                sku['full_name'] = item.title
                sku['price'] = item.price
                sku['features'] = item.features
                sku['brand'] = item.brand
                sku['detail_page_url'] = item.detail_page_url
                sku['s_pic'] = item.small_pic
                sku['m_pic'] = item.medium_pic
                sku['l_pic'] = item.large_pic
                sku['is_instock'] = True
                sku['is_prime'] = True if item.is_prime else False

            pprint.pprint(sku)

    def parse_spu(self):
        '''通过 AMAZON API 获取 SPU 的详细数据'''
        print('\n>>> Parsing SPU...')
        spu_asin = self.spu.get('asin')
        if spu_asin:
            # 请求。
            item = AmazonLookupItem(spu_asin)
            self.spu['name'] = item.title
            self.spu['features'] = item.features
            self.spu['detail'] = item.get_detail(self.page_doc)
            self.spu['brand'] = item.brand
            self.spu['detail_page_url'] = item.detail_page_url
            self.spu['url'] = self.id2url(spu_asin)
            self.spu['max_price'] = max([sku['price'] for sku in self.sku_list if sku.get('price', None)])
            self.spu['min_price'] = min([sku['price'] for sku in self.sku_list if sku.get('price', None)])
            self.spu['s_pic'] = item.small_pic
            self.spu['m_pic'] = item.medium_pic
            self.spu['l_pic'] = item.large_pic

            pprint.pprint(self.spu)

    def get_hires_pic_urls(self, asin):
        '''获取高清大图'''
        # 请求。
        url = self.id2url(asin)
        response, doc = get_html_doc(url)
        # script 标签里面的内容。
        scripts = doc.xpath('//script/text()')
        # 匹配 url 的正则表达式。
        url_re = re.compile(r'hiRes":"(\S{,200})","thumb')
        # 一般会有两组结果，遇到有结果的返回，注意：这里忽略了第二组。
        for s in scripts:
            urls = url_re.findall(s)
            if urls:
                return urls

    def parse_hires_pic_urls(self):
        '''获取此 item_id 的高清大图。如果此商品有其他 sku 则需要另外获取。'''
        print('\n>>> Initializing item HiRes pictures...')

        # 获取 SKU 高清图。
        for sku in self.sku_list:
            asin = sku.get('asin')
            sku['hd_pics'] = self.get_hires_pic_urls(asin)
            print('''\n>>> Got SKU's HiRes pictures of %s:''' % asin)
            pprint.pprint(sku['hd_pics'])

        # 获取 SPU 高清图。
        spu_asin = self.spu.get(asin)
        self.spu['hd_pics'] = self.get_hires_pic_urls(asin)
        print('''\n>>> Got SPU's HiRes pictures of %s:''' % asin)
        pprint.pprint(self.spu['hd_pics'])

    def lc_save(self):
        '''保存到 leancloud。'''
        print('\n>>> Saving to Leancloud...')

        # 保存 SPU。
        Spu = leancloud.Object.extend('Spu')
        spu = Spu()
        spu.set(self.spu)
        spu.save()
        print('SPU saved.')

        # 保存 SKU。
        Sku = leancloud.Object.extend('Sku')
        skus = [Sku().set(sku) for sku in self.sku_list]
        skus = [sku.set('spu', spu) for sku in skus]
        leancloud.Object.save_all(skus)
        print('SKU saved.')


def print_products(products):
    with open('result.txt', 'w') as f:
        for i, product in enumerate(products):
            line = "{0}. '{1}'".format(i, product.title.encode('utf8'))
            print(line)
            f.write(line + '\n')


# 发送请求，带 cookie。
def get_html_doc(url):
    time.sleep(0.9)
    headers = {
        'User-Agent': ua.random,
        'Cookie': AMZ_COOKIE
    }
    response = requests.get(
        url,
        headers=headers)
    print('Response code: %d' % response.status_code)
    return [response, html.fromstring(response.content)]


# 解决中文乱码问题。
def write_html_file(response):
    with open('html.txt', 'w') as f:
        f.write(response.text.encode('utf-8').decode('gbk', 'ignore'))


# 获取 amazon 页面产品的高清大图。
def get_amazon_hires_pic_urls(url):
    '''获取高清大图'''
    # 请求。
    response, doc = get_html_doc(url)
    # script 标签里面的内容。
    scripts = doc.xpath('//script/text()')
    # 匹配 url 的正则表达式。
    url_re = re.compile(r'hiRes":"(\S{,200})","thumb')
    # 一般会有两组结果，遇到有结果的返回，注意：这里忽略了第二组。
    for s in scripts:
        urls = url_re.findall(s)
        if urls:
            return urls


if __name__ == '__main__':
    VALID_AMZ_INDEX = [
        'All',
        'Apparel',
        'Appliances',
        'ArtsAndCrafts',
        'Automotive',
        'Baby',
        'Beauty',
        'Blended',
        'Books',
        'Classical',
        'Collectibles',
        'DVD',
        'DigitalMusic',
        'Electronics',
        'GiftCards',
        'GourmetFood',
        'Grocery',
        'HealthPersonalCare',
        'HomeGarden',
        'Industrial',
        'Jewelry',
        'KindleStore',
        'Kitchen',
        'LawnAndGarden',
        'Marketplace',
        'MP3Downloads',
        'Magazines',
        'Miscellaneous',
        'Music',
        'MusicTracks',
        'MusicalInstruments',
        'MobileApps',
        'OfficeProducts',
        'OutdoorLiving',
        'PCHardware',
        'PetSupplies',
        'Photo',
        'Shoes',
        'Software',
        'SportingGoods',
        'Tools',
        'Toys',
        'UnboxVideo',
        'VHS',
        'Video',
        'VideoGames',
        'Watches',
        'Wireless',
        'WirelessAccessories'
    ]
    url = input('Enter Amazon.cn URL: ')
    p = AmzProduct(url)
