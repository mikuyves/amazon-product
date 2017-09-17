# coding: utf-8

from datetime import datetime
import json

from flask import Flask
from flask import render_template
from flask_sockets import Sockets

from flask_bootstrap import Bootstrap

import leancloud

from views.todos import todos_view

app = Flask(__name__)
sockets = Sockets(app)
bootstrap = Bootstrap(app)

# 动态路由
app.register_blueprint(todos_view, url_prefix='/todos')

Spu = leancloud.Object.extend('Spu')
Sku = leancloud.Object.extend('Sku')
History = leancloud.Object.extend('History')

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/time')
def time():
    return str(datetime.now())


@app.route('/pd/<asin>')
def product(asin):
    query = Sku.query
    query.equal_to('asin', asin)
    sku = query.first()
    return json.dumps(sku.dump())


@sockets.route('/echo')
def echo_socket(ws):
    while True:
        message = ws.receive()
        ws.send(message)
