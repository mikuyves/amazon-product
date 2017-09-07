# coding=utf-8
import re
from lxml import html
import requests
from amazon.api import AmazonAPI
import bottlenose.api
from secret import AMZ_ACCESS_KEY, AMZ_SECRET_KEY, AMZ_ASSOC_TAG


region_options = bottlenose.api.SERVICE_DOMAINS.keys()
amazon = AmazonAPI(
    AMZ_ACCESS_KEY,
    AMZ_SECRET_KEY,
    AMZ_ASSOC_TAG,
    region='CN',
    MaxQPS=0.9
)


def search_products(keywords, search_index):
    return amazon.search(Keywords=keywords, SearchIndex=search_index)


def print_products(products):
    # product.featrues: List: 商品详情

    with open('result.txt', 'w') as f:
        for i, product in enumerate(products):
            line = "{0}. '{1}'".format(i, product.title.encode('utf8'))
            print line
            f.write(line + '\n')


def find_big_picture(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    }
    page = requests.get(url,headers=headers)
    return page


def get_content(item_id):
    url = "http://www.amazon.cn/dp/" + item_id
    print "Processing: "+url
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
