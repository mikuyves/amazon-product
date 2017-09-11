# coding=utf8
import json
import re
import requests
from lxml import html

from search import amz_product

def search_in_js():
    pattern = re.compile(r"var dataToReturn = ({((\n|.)*)});", re.MULTILINE)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    }
    response = requests.get(
        "https://www.amazon.cn/Hello-Kitty-PANTS/dp/B01MSWBWHF/ref=cts_ap_1_fbt",
        headers=headers)


    doc = html.fromstring(response.content)
    scripts= [s for s in doc.xpath('//script/text()') if 'dataToReturn' in s]
    script = scripts[0]
    sku_re = re.compile(r'dimensionValuesDisplayData" : (.*),')
    sku_raw_data = sku_re.search(script).group(1)
    skus = json.loads(sku_raw_data)
    return skus

def by_item_id(item_id):
    # item_id = 'B0736CM23N'
    p = amz_product.lookup(ItemId=item_id)
    return p.price_and_currency

def by_item_node(item_id):
    p = amz_product.lookup(ItemId=item_id)
    return p

def search_stephen_baby():
    results = amz_product.search(
        Keywords='Hello Kitty',
        SearchIndex='Baby',
        BrowseNode='1403206071'  # 海外购
    )

    products = []
    for i, r in enumerate(results):
        print(i, r.asin, r.is_prime, r.title.encode('utf8'), r.price_and_currency)
        products.append(r)

    return products


def by_item_id2():
    item_id = 'B0736CM23N'
    p = amz.lookup(ItemId=item_id)
    return p
