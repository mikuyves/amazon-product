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
    AMZ_ACCESS_KEY2, AMZ_SECRET_KEY2, AMZ_ASSOC_TAG2,\
    LC_APP_ID, LC_APP_KEY
from models import Prod, Sku

COOKIE = 'amznacsleftnav-48d7533c-de56-3cba-938d-d0cc3a768cb7=1; amznacsleftnav-06e17069-7503-3692-b959-7d3aef8ce92c=1,5; __utma=164006624.836544999.1503952096.1504989263.1504991980.3; __utmz=164006624.1504991980.3.3.utmccn=(referral)|utmcsr=docs.aws.amazon.com|utmcct=/AWSECommerceService/latest/GSG/GettingStarted.html|utmcmd=referral; __utmv=164006624.vivian01-23; s_fid=40921BF39D240D33-29A4C77D01187C48; s_nr=1505002469874-Repeat; s_vnum=1935500993603%26vn%3D3; s_dslv=1505002469875; x-wl-uid=1ehYeIe6chM+z7t4O0bMSi2m+cWzISKIST07SWjj/QsNE93Rbtd44TD8sDdsRVtpbD4Nkh9mPQrDHnpnXb+p8tXJ8HFIyJ7ttynsRSRnCrqXipcMiCb8Wr9yH0D4FJlsa9jYDiMpWHNw=; amznacsleftnav-9f9844ea-0931-34d4-ab98-9eaac10dd320=1; amznacsleftnav-59c8e658-3621-3d71-8913-5ad0bd4d3143=1,6,7,8; UserPref=U5eErzEOh7Kb13ApetefsvOFijLFIYrE7wG7RCwoP7wGQ1lMFf9w69rJhITQ035KfS5bTxnWhipkjMUpL3cYbsMT7YmLAA2rU0ntq6niVBrTxmGdhlYmRy9dxbKMXHSDqVbwgp6f9d8J1R9+0wCaFUbUMkUuWOTcEGI76Z6p71ebAhFGXVBcQD3KCYi1kTVBgypf38cgmVYCADm8Evw7qQLdBbDcVBmBQ+ShyL4HzppoVWdSDU8ZaTRgYdzaGKNcnOyzfpU3uRXM+ykCXXVoCh1P11ysj27i6k2i+GfLCniJiEDlW81zeOaZeFj+ng/Ngs2+njz4nD25kOUGZmnSVh8APVlcfpfQVusMf7SR3CkGgEcGyx/LWwWd36Qv1gss5zinYoesgKM9IwgBCYtJSg30aisF+CkvFCkZ3pm1abn1Jp656f6Oy+FPOHn61so3; lc-acbcn=zh_CN; session-token="R6ASJ0cOxsmr9TOtfsMqgbSv1J51U9AjQGAf+l2/0XvUznNJbakqYo4OK0u2xvLW8PgWXVSt7NXutNLIQfQVGv15RS3p+6JzxOqdiLpBQZxRmX6WbsCDOp5OsbohbHgj7x+K+QSrIGLa2KcOnkoiuzcAWWeDcOF6RdBqUOgMRQZBUkCbZo7tb3DQw6EIV//NDL5swaZV58GnaNAPYceJbmGIiOUxVcjxhA06jx6MlPTBG8kz3hptxmilfC2QjT+m+oL13jOiKAk="; x-acbcn="8o@fXDFRx?KeaaBbpq3LzJ5ldYd@A8tpqqTQA0WfSJcEOIi7LDGZE8e40Et?b1sO"; at-main=Atza|IwEBIMMP70elSgNmjJZ0tLseGTTiqAiBENGXH5SlnSFYue1Ol3N4iBUK5kyYFnwzKzE9HpdQvYhJ_igjk6cFTyihZP1ZWAbKgyvw1pjYr3y_mTjkA6jFDYi09LIV0lmq9wUnNc7ZlBbes4cilDzjqtsEsST5s7CAtknoA59Gq1c5auqkOR_D9CrxS9DkeTOMLQLL6nqNk6-U5WCk48EHh1ZEv8mDa36KUpf4a36DV8l3Yw8q1HPP8hGr5wuO5JdJVYk5EDGyldx5WF0QG9BWpZ8u__HxVmLlE5nCPN488fT0pHfWjh2FjalmNiH_GFRiichpHRq9EP3PBHl1t2VzKxwKx3F71nQJ27FAzaALgrMbMtcar54_7M6E8ZZ8fA3tI-HV8iMe-h1FLdEV31sFNCpWuN65; sess-at-main="bDCi/6xsGf+yS4gsvMsDo+NGqvSP2cps8Hakj3+U3FQ="; csm-hit=s-4Q25V7ZV8QE3MFW0346M|1505357433973; ubid-acbcn=456-7902547-2180623; session-id-time=2082729601l; session-id=457-4897587-8039847'

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
        'Cookie': COOKIE
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
