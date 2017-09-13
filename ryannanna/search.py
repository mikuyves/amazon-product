# coding=utf-8
import re
import json
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
    AMZ_ACCESS_KEY2, AMZ_SECRET_KEY2, AMZ_ASSOC_TAG2,\
    LC_APP_ID, LC_APP_KEY
from models import Prod, Sku


# 初始化 Leancloud 应用。
leancloud.init(LC_APP_ID, LC_APP_KEY)

ua = UserAgent()


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

# region_options = bottlenose.api.SERVICE_DOMAINS.keys()

amz_product = AmazonAPI(*AUTH_ARGS, **AUTH_KWARGS)

amz_scraper = AmazonScraper(*AUTH_ARGS, **AUTH_KWARGS)

amz_nose = bottlenose.Amazon(
    Parser=lambda text: BeautifulSoup(text, 'xml'),
    *AUTH_ARGS,
    **AUTH_KWARGS)


class AmzProduct(object):
    def __init__(self, url):
        # 处理基本信息： url 和 asin。
        self.raw_url = url
        self.item_id = self.url2id(url)
        self.url = self.id2url(self.item_id)

        # 抓取网页源代码内容。
        print('\n>>> Parsing item URL...')
        self.page_doc = get_html_doc(self.url)
        print('\n>>> Sleep for 0.9s...')
        time.sleep(0.9)
        # 通过 amazon api 获取 asin=item_id 的商品信息。可能是 prod 的 spu 或 其中一个 sku。
        print('\n>>> Getting info from Amazon api...')
        self.item_api = self.lookup_by_asin(self.item_id)

        # 生成 spu 和 sku。
        print('\n>>> Initializing SPU and SKU...')
        self.spu, self.sku_list = self.init_spu_and_sku()
        # 获取此 item_id 的高清大图。如果此商品有其他 sku 则需要另外获取。
        print('\n>>> Initializing item HiRes pictures...')
        self.init_hires_pic_urls()

    def lookup_by_asin(self, asin):
        p = AmazonAPI(*AUTH_ARGS, **AUTH_KWARGS)
        return p.lookup(ItemId=asin)

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
                sku_list.append(sku)

        else:
            print('This product has no SKU.')
            spu = {'asin': self.item_id}
            sku_list = [spu]

        print('Got SPU and SKU.')
        print(spu)
        print(sku_list)
        return [spu, sku_list]

    def get_hires_pic_urls(self, page_doc):
        # script 标签里面的内容。
        scripts = page_doc.xpath('//script/text()')
        # 匹配 url 的正则表达式。
        url_re = re.compile(r'hiRes":"(\S{,200})","thumb')
        # 一般会有两组结果，遇到有结果的返回，注意：这里忽略了第二组。
        for s in scripts:
            urls = url_re.findall(s)
            if urls:
                return urls

    def init_hires_pic_urls(self):
        urls = self.get_hires_pic_urls(self.page_doc)
        for sku in self.sku_list:
            if sku.get('asin') == self.item_id:
                sku['hires_pics'] = urls
                print('\n>>> Got HiRes pictures of %s:' % self.item_id)
                print(urls)


def print_products(products):
    # product.featrues: List: 商品详情

    with open('result.txt', 'w') as f:
        for i, product in enumerate(products):
            line = "{0}. '{1}'".format(i, product.title.encode('utf8'))
            print(line)
            f.write(line + '\n')


def get_html_doc(url):
    headers = {
        'User-Agent': ua.random
    }
    response = requests.get(
        url,
        headers=headers)
    return html.fromstring(response.content)


def find_big_picture(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    }
    page = requests.get(url,headers=headers)
    return page


def get_products_by_ids(ids):
    products = []
    for id in ids:
        p = amz_product.lookup(ItemId=id)
        print(p.asin, p.title, p.price_and_currency)
        products.append(p)
    return product_data_to_json(products)


def product_data_to_json(data):
    if len(data) == 1:
        p_data = data[0]
        prod = {
            'name': p_data.title,
            'price': float(p_data.price_and_currency[0])
        }
        skus = [prod]
    if len(data) > 1:
        p_data = data.pop(0)
        prod = {
            'name': p_data.title,
            'max_price': max([float(d.price_and_currency[0]) for d in data]),
            'min_price': min([float(d.price_and_currency[0]) for d in data]),
        }
        # 保存到 Leancloud。
        lc_prod = Prod()
        lc_prod.set(prod)
        lc_prod.save()

        skus = []
        for d in data:
            sku = {
                'full_name': d.title,
                'price': float(d.price_and_currency[0])
            }
            skus.append(sku)
            # 保存到 Leancloud。
            # 保存到 Leancloud。
            lc_sku = Sku()
            lc_sku.set(sku)
            lc_sku.save()

    return {'prod': prod, 'skus': skus}


def get_products_from_url(url):
    data = get_spu_and_skus(url)
    if len(data) == 1:
        ids = data
    elif len(data) ==2:
        ids = [data[0]] + list(data[1].keys())
    return get_products_by_ids(ids)


def get_content(item_id):
    url = "http://www.amazon.cn/dp/" + item_id
    print("Processing: "+url)
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}
    page = requests.get(url,headers=headers)
    doc = html.fromstring(page.content)

    XPATH_NAME = '//h1[@id="title"]//text()'
    XPATH_SALE_PRICE = '//span[contains(@id,"ourprice") or contains(@id,"saleprice")]/text()'
    XPATH_ORIGINAL_PRICE = '//td[contains(text(),"List Price") or contains(text(),"M.R.P") or contains(text(),"Price")]/following-sibling::td/text()'
    XPATH_CATEGORY = '//a[@class="a-link-normal a-color-tertiary"]//text()'
    XPATH_AVAILABILITY = '//div[@id="availability"]//text()'

    return doc


def match_url(doc):
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
    keywords = raw_input('Enter keywords: ')
    search_index = raw_input('''
    Valid values of SearchIndex are: 
    'All','Apparel','Appliances','ArtsAndCrafts','Automotive', 'Baby','Beauty',
    'Blended','Books','Classical','Collectibles','DVD','DigitalMusic','Electronics',
    'GiftCards','GourmetFood','Grocery','HealthPersonalCare','HomeGarden','Industrial',
    'Jewelry', 'KindleStore','Kitchen','LawnAndGarden','Marketplace','MP3Downloads',
    'Magazines','Miscellaneous', 'Music','MusicTracks','MusicalInstruments','MobileApps',
    'OfficeProducts','OutdoorLiving','PCHardware', 'PetSupplies','Photo','Shoes',
    'Software','SportingGoods','Tools','Toys','UnboxVideo','VHS','Video', 'VideoGames',
    'Watches','Wireless','WirelessAccessories'

    Enter keywords: 
    ''')
    products = search_products(keywords, search_index)
    print_products(products)
