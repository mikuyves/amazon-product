import json
import re

from search import AmzProduct, get_html_doc


print('Lets go')

url = 'https://www.amazon.cn/s/ref=sr_pg_2?fst=as%3Aoff&rh=n%3A2016156051%2Cn%3A2152158051%2Cn%3A2152156051%2Cn%3A2153534051%2Ck%3Ajuicy&page=2&keywords=juicy&ie=UTF8&qid=1505271194'

doc = get_html_doc(url)
print(doc)

results = doc.xpath('//@href')
print(results)
link_re = re.compile('^https://www.amazon.cn/\S+')


links = []
for r in results:
    link = link_re.search(r)
    if link:
        print(link.group(0))
        links.append(link.group(0))

# search every link
for link in links[1:]:
    print('Parsing %s' % link)
    p = AmzProduct(link)

    print(p.sku_list)
    sku_list6 = [sku for sku in p.sku_list if sku.get('name') and '6' in sku.get('name')]

    with open('juicy.txt', 'a') as f:
        f.write('6 years old: \n')
        json.dump(sku_list6, f)
    print(sku_list6)
