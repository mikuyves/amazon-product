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
# from fake_useragent import UserAgent
# from fake_useragent import FakeUserAgentError

from secret import AMZ_ACCESS_KEY, AMZ_SECRET_KEY, AMZ_ASSOC_TAG,\
    AMZ_ACCESS_KEY2, AMZ_SECRET_KEY2, AMZ_ASSOC_TAG2, AMZ_COOKIE,\
    LC_APP_ID, LC_APP_KEY, LC_USERNAME, LC_PASSWORD


# Leancloud
# 初始化 Leancloud 应用。
leancloud.init(LC_APP_ID, LC_APP_KEY)

# 登陆 Leancloud 应用。
user = leancloud.User()
user.login(LC_USERNAME, LC_PASSWORD)
print(user)

# 初始化所需要的类。
Sku = leancloud.Object.extend('Sku')
Spu = leancloud.Object.extend('Spu')
History = leancloud.Object.extend('History')

# try:
#     ua = UserAgent(
#         cache=False,
#         use_cache_server=False,
#         fallback='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36',
#     )
# except FakeUserAgentError:
#     pass
#
# print(ua.random)

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36'

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
    def __init__(self, url, DEBUG=False):
        # 处理基本信息： url 和 asin。
        self.raw_url = url
        self.item_id = self.url2id(url)
        self.url = self.id2url(self.item_id)

        # 判断是新建还是更新。
        is_saved = self.check_is_saved()
        if is_saved:
            print('This item already exists in cloud data.')
            print('Now, updating...\n')

        # 抓取网页源代码内容。
        # 通过源码获取，spu 及 sku 信息，这一步一定要做。因为每次获取都可能会不同。
        # 网页上数据会显示什么 sku 在售。如果更新的时候发现之前的 sku asin 不在
        # 网页上，就表示这个 sku 已经不能购买。需要更新云端中 is_instock 的字段。
        print('\n>>> Parsing item URL...')
        self.response, self.page_doc = get_html_doc(self.url)

        # 通过 amazon api 获取 asin=item_id 的商品信息。可能是 prod 的 spu 或 其中一个 sku。
        print('\n>>> Getting info from Amazon api...')
        self.item_api = AmazonLookupItem(self.item_id)

        # 生成此 item 的 spu 和 sku_list。
        print('\n>>> Initializing SPU and SKU...')
        self.spu, self.sku_list = self.init_spu_and_sku()

        if not DEBUG:
            self.parse_and_save(update=is_saved)

    def parse_and_save(self, update=False):
        # 获取所有 SKU 和 SPU 的详细数据。注意顺序，首先分析 SKU。
        self.parse_sku_list()
        self.parse_spu()
        if not update:
            self.parse_hires_pic_urls()
        self.lc_save(update=update)

    def __str__(self):
        if self.spu.get('name'):
            return self.spu['name']
        else:
            return self.item_id

    def check_is_saved(self):
        spu_query = Spu.query.equal_to('asin', self.item_id).find()
        sku_query = Sku.query.equal_to('asin', self.item_id).find()
        return True if (spu_query or sku_query) else False

    def url2id(self, url):
        url_re = re.compile(r'/(dp|gp/product)/(\S{,10})')
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
                'url': self.url
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
            self.spu['sku_number'] = len(self.sku_list)

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
            urls = self.get_hires_pic_urls(asin)
            # 预防 amazon 修改 html。
            if urls:
                sku['hd_pics'] = urls
            print('''\n>>> Got SKU's HiRes pictures of %s:''' % asin)
            pprint.pprint(sku.get('hd_pics'))

        # 获取 SPU 高清图。
        asin = self.spu.get('asin')
        self.spu['hd_pics'] = self.get_hires_pic_urls(asin)
        print('''\n>>> Got SPU's HiRes pictures of %s:''' % asin)
        pprint.pprint(self.spu.get('hd_pics'))


    # 保存到 leancloud。
    def lc_save(self, update=False):
        print('\n>>> Saving to Leancloud...')

        # 保存 SPU。
        if update:
            spu = Spu.query.equal_to('asin', self.spu.get('asin')).first()
        else:
            spu = Spu()
        spu.set(self.spu)
        spu.save()
        print('SPU saved.')

        # 保存 SKU。
        # 更新。
        if update:
            skus = []
            for sku in self.sku_list:
                results = Sku.query.equal_to('asin', sku.get('asin')).find()
                # Update, Exists.
                if results:
                    sku_obj = results[0]
                    price = sku.get('price')
                    previous_price = sku_obj.get('price')
                    increment = price - previous_price
                    change_rate = increment / previous_price
                    sku_obj.set(sku)
                    sku_obj.set('increment', increment)
                    sku_obj.set('change_rate', change_rate)
                # Add, New.
                else:
                    sku_obj = Sku()
                    sku_obj.set(sku)
                    sku_obj.set('spu', spu)
                    sku_obj.set('increment', 0.0)
                    sku_obj.set('change_rate', 0.0)
                    # Only new sku need to get hd pics advoiding HTML changed by Amazon.
                    hd_pic_urls = self.get_hires_pic_urls(sku.get('asin'))
                    sku_obj.set('hd_pics', hd_pic_urls)
                skus.append(sku_obj)

            # Update, Old. Check SKU out of stock:
            old_sku_objs = Sku.query.equal_to('spu', spu).find()
            new_sku_asins = [sku.get('asin') for sku in self.sku_list]
            for old_sku_obj in old_sku_objs:
                if old_sku_obj.get('asin') not in new_sku_asins:
                    old_sku_obj.set('is_instock', False)
                    skus.append(old_sku_obj)

        # 新建。
        else:
            skus = [Sku().set(sku) for sku in self.sku_list]
            skus = [sku.set('spu', spu) for sku in skus]

        leancloud.Object.save_all(skus)
        print('SKU saved.')

        # 保存历史价格，prime 属性及库存情况。
        self.lc_save_sku_history(skus)
        # 更新历史最高及最低价格。
        self.check_history_price(skus)

    # 保存历史价格，prime 属性及库存情况。
    def lc_save_sku_history(self, skus):
        lines = []
        for sku in skus:
            line = History()
            line.set('sku', sku)
            line.set('asin', sku.get('asin'))
            line.set('price', sku.get('price'))
            line.set('is_instock', sku.get('is_instock'))
            line.set('is_prime', sku.get('is_prime'))
            line.set('increment', sku.get('increment'))
            line.set('change_rate', sku.get('change_rate'))
            lines.append(line)
        leancloud.Object.save_all(lines)

    # 对比历史价格，记录历史最高及最低价格。
    def check_history_price(self, skus):
        for sku in skus:
            price = sku.get('price')
            lines = History.query\
                .equal_to('sku', sku) \
                .add_descending('updatedAt')\
                .find()

            prices  = [line.get('price') for line in lines]

            spu_max_price = self.spu.get('max_price')
            off_to_spu = price / spu_max_price
            top_price = max(prices)
            bottom_price = min(prices)
            is_top = price == top_price  # 历史新高
            is_bottom = price == bottom_price  # 历史新低。

            # 上一次记录价格。
            if len(lines) == 1:
                previous_price = price  # 未有记录。
            elif len(lines) > 1:
                previous_price = prices[1]  # 已有记录，排第二。
            else:
                # TODO: 提取成 exception。
                print('There is something wrong with the SKU History.')
                print('Please check ASIN: %s.' % sku.get('asin'))
                continue

            increment = price - previous_price  # 对比上一次记录的增量。
            change_rate = increment / previous_price
            history_increment = price - top_price  # 对比历史最高价的增量。
            change_history_rate = history_increment / top_price

            # 记录价格变化频率。
            for line in lines:
                change = line.get('increment', 0.0)
                last_change = change  # 最近一次价格变化量。即最近一次非零的 increment。
                last_change_rate = line.get('change_rate', 0.0)  # 最近一次价格变化率。
                last_change_time = (
                    lines[0].get('createdAt') - line.get('createdAt')
                ).total_seconds()  # 对上一次更新价格持续的时间，单位为：秒。
                # 一直查询至有增量变化记录为止。
                if change:
                    break

            sku.set('top_price', top_price)
            sku.set('bottom_price', bottom_price)
            sku.set('is_top', is_top)
            sku.set('is_bottom', is_bottom)
            sku.set('increment', increment)
            sku.set('change_rate', change_rate)
            sku.set('history_increment', history_increment)
            sku.set('change_history_rate', change_history_rate)
            sku.set('last_change', last_change)
            sku.set('last_change_rate', last_change_rate)
            sku.set('last_change_time', last_change_time)
            sku.set('off_to_spu', off_to_spu)
        leancloud.Object.save_all(skus)


def update_item(url=None):
    if not url:
        spu = Spu.query.add_ascending('updatedAt').first()
        url = spu.get('url')
    item = AmzProduct(url)
    return item


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
        'User-Agent': user_agent,
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
    # url = input('Enter Amazon.cn URL: ')
    url = 'https://www.amazon.cn/%E6%AF%8D%E5%A9%B4%E7%94%A8%E5%93%81/dp/B0159W8OOW/ref=sr_1_1?s=amazon-global-store&ie=UTF8&qid=1505512954&sr=8-1&keywords=stephan+baby'
    p = AmzProduct(url)
