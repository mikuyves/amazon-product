# coding: utf-8

import leancloud
from leancloud import Engine
from leancloud import LeanEngineError
import json
import search
from secret import LC_USERNAME, LC_PASSWORD

engine = Engine()

user = leancloud.User()
user.login(LC_USERNAME, LC_PASSWORD)

@engine.define
def hello(**params):
    if 'name' in params:
        return 'Hello, {}!'.format(params['name'])
    else:
        return 'Hello, LeanCloud!'


@engine.define
def parse_new_item(**params):
    if 'url' in params:
        item = search.AmzProduct(params['url'])
        return [item.spu, item.sku_list]
    else:
        return 'Hello, LeanCloud!'


@engine.define
def update_item(**params):
    item = search.update_item()
    return [item.spu, item.sku_list]


@engine.before_save('Todo')
def before_todo_save(todo):
    content = todo.get('content')
    if not content:
        raise LeanEngineError('内容不能为空')
    if len(content) >= 240:
        todo.set('content', content[:240] + ' ...')
