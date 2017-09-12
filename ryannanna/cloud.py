# coding: utf-8

from leancloud import Engine
from leancloud import LeanEngineError
import json
import search

engine = Engine()


@engine.define
def hello(**params):
    if 'name' in params:
        return 'Hello, {}!'.format(params['name'])
    else:
        return 'Hello, LeanCloud!'


@engine.define
def test(**params):
    if 'url' in params:
        products = search.get_products_from_url(params['url'])
        return products
    else:
        return 'Hello, LeanCloud!'


@engine.before_save('Todo')
def before_todo_save(todo):
    content = todo.get('content')
    if not content:
        raise LeanEngineError('内容不能为空')
    if len(content) >= 240:
        todo.set('content', content[:240] + ' ...')
