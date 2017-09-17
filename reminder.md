```html
<td class="a-span12 a-size-base">
    <span id="ddmMerchantMessage">由<b>亚马逊美国</b>从境外直接销售并发货, 购买行为受亚马逊海外购使用条件和美国法律的约束。
    <a href="https://www.amazon.cn/gp/help/customer/display.html/ref=dp_ags_ddm_cou?ie=UTF8&nodeId=201625060" target="_blank">了解更多。</a>
    </span>
</td>
```

Leancloud
=========

返回结果可以直接返回 dict, list
结果会经过 JSON 系列化后 
在 result 里面

#### 与 JS 不同
* 保存对象
```python
import leancloud


# 保存一个对象。
prod = leancloud.Object.extend('Prod')  # 新建一个对象。
prod.set(data_dict)  # 设置字段值。
prod.save()  # 保存到云端。


# 保存多个对象。
sku_list = []
for sku_dict in data_list:
    sku = leancloud.Object.extend('Sku')
    sku.set(sku_dict)
    sku_list.append(sku)
    
# 或者一句：
sku_list = [leancloud.Object.extend('Sku').set(sku_dict) for sku_dict in data_list]

leancloud.Object.save_all(sku_list)

```
十分简单，保存后 prod 直接是一个有 id 的 leancloud 对象。
不需要像 js 那样，赋值给一个变量再使用。



Amazon Api
==========

#### 库存情况
api 只返回最短信息
如果要完整库存情况需要在实际零售网页上查看。

    The value returned by the Availability element may not match the one on 
    the Amazon retail web site's product detail page because typically there 
    is a short and long version of an availability message. Product Advertising 
    API returns the short version. The more verbose availability message is
     used on the retail web site.
     
     http://docs.aws.amazon.com/AWSECommerceService/latest/DG/AvailabilityValues.html
     

AmzProduct
==========
#### 关于获取详情及获取高清图片
虽然在第一次初始化的时候就可以获取 SPU 或其中一个 SKU 的详情和高清图片。但是，这个 SPU 或 SKU 的 ASIN 是随机的。
如果在初始化的过程中就获取，使得整个类的方法高耦合。
所以，把获取详情（使用 api）和获取高清图片（使用 requests）抽离出来，不在初始化的时候处理。
宁愿多花一次请求的时间，也应该将方法解耦出来。

#### 问题
 * [x] 没有 SKU 的单品，获取不了 hires pics。
     * 原因：写错变量名。
 
#### TODO
* [ ] 检查，更新，SKU，与之前历史对比。