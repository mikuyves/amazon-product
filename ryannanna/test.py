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

from secret import LC_APP_ID, LC_APP_KEY, LC_USERNAME, LC_PASSWORD


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


def get_data():
    spu = Spu.query.add_descending('updatedAt').first()
    skus = Sku.query.equal_to('spu', spu).find()

    return [spu, skus]
