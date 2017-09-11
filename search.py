# coding=utf-8
import re
import json
import time
from lxml import html
import requests
from amazon.api import AmazonAPI
import bottlenose.api

import bottlenose
from bs4 import BeautifulSoup
from amazon_scraper import AmazonScraper

from secret import AMZ_ACCESS_KEY, AMZ_SECRET_KEY, AMZ_ASSOC_TAG, AMZ_ACCESS_KEY2, AMZ_SECRET_KEY2, AMZ_ASSOC_TAG2

import random
import time
from urllib.error import HTTPError


def error_handler(err):
    ex = err['exception']
    if isinstance(ex, HTTPError) and ex.code == 503:
        time.sleep(random.expovariate(0.1))
        return True


auth_args = [AMZ_ACCESS_KEY, AMZ_SECRET_KEY, AMZ_ASSOC_TAG]
auth_kwargs = {
    'Region': 'CN',
    'MaxQPS': 0.9,
    'Timeout': 5.0,
    'ErrorHandler': error_handler}


# region_options = bottlenose.api.SERVICE_DOMAINS.keys()

amz_product = AmazonAPI(*auth_args, **auth_kwargs)

amz_scraper = AmazonScraper(*auth_args, **auth_kwargs)

amz_nose = bottlenose.Amazon(
    Parser=lambda text: BeautifulSoup(text, 'xml')
    *auth_args,
    **auth_kwargs)


def search_products(keywords, search_index):
    return amazon.search(Keywords=keywords, SearchIndex=search_index)


def print_products(products):
    # product.featrues: List: 商品详情

    with open('result.txt', 'w') as f:
        for i, product in enumerate(products):
            line = "{0}. '{1}'".format(i, product.title.encode('utf8'))
            print(line)
            f.write(line + '\n')


def url2id(url):
    url_re = re.compile(r'/dp/(\S+)/')
    return url_re.search(url).group(1)


def id2url(id):
    return 'https://www.amazon.cn/dp/{id}/'.format(id=id)


def trans_url(copied_url):
    return id2url(url2id(copied_url))


def get_html_doc(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    }
    response = requests.get(
        url,
        headers=headers)
    return html.fromstring(response.content)


def get_spu_and_skus(url):
    # pattern = re.compile(r"var dataToReturn = ({((\n|.)*)});", re.MULTILINE)
    url = trans_url(url)
    doc = get_html_doc(url)

    # 产品 SPU 及 SKU 数据的 scirpt 标签内容。
    scripts= [s for s in doc.xpath('//script/text()') if 'dataToReturn' in s]
    script = scripts[0]

    # SKU 列表及详情。
    spu_re = re.compile(r'"parentAsin" : "(.*)"')
    spu_id = spu_re.search(script).group(1)

    # SKU 数据格式：
    # key: asin  :  value: [尺寸1， 尺寸2， 颜色]
    # B01IJWFCQC [u'Baby', u'9 \u4e2a\u6708', u'Best Day Evert']
    sku_re = re.compile(r'"dimensionValuesDisplayData" : (.*),')
    sku_raw_data = sku_re.search(script).group(1)
    skus = json.loads(sku_raw_data)
    return [spu_id, skus]


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
    return products


def get_products_from_url(url):
    data = get_spu_and_skus(url)
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
