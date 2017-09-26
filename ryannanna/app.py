# coding: utf-8

from datetime import datetime
import json

from flask import Flask
from flask import render_template, request, session, redirect, url_for
from flask_sockets import Sockets
from flask_mongoengine.pagination import Pagination

from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_moment import Moment
from wtforms import StringField, SubmitField
from wtforms.validators import Required

import leancloud

from views.todos import todos_view
from search import update_item


app = Flask(__name__)
sockets = Sockets(app)
bootstrap = Bootstrap(app)
moment = Moment(app)
app.config['SECRET_KEY'] = 'hard to guess string'


# 动态路由
app.register_blueprint(todos_view, url_prefix='/todos')


Spu = leancloud.Object.extend('Spu')
Sku = leancloud.Object.extend('Sku')
History = leancloud.Object.extend('History')


class UrlForm(FlaskForm):
    url = StringField('Enter the URL:', validators=[Required()])
    submit = SubmitField('Submit')


@app.route('/', methods=['GET', 'POST'])
def index():
    # Pagination.
    page = request.args.get('page', 1, type=int)
    spu_all = Spu.query.add_descending('createdAt').find()
    pg = Pagination(spu_all, page, 20)

    # Get and arrange the item data to render.
    items = []
    for spu_obj in pg.items:
        spu = spu_obj.dump()
        sku_objs = Sku.query \
            .equal_to('spu', spu_obj) \
            .add_ascending('price').find()
        skus = [sku_obj.dump() for sku_obj in sku_objs]
        items.append({'spu': spu, 'skus': skus})

    # Form to input the URL.
    url = None
    form = UrlForm()
    if form.validate_on_submit():
        url = form.url.data
        item = update_item(url)
        form.url.data = ''
        return redirect(url_for('index'))

    return render_template('index.html',
                           form=form,
                           items=items,
                           pagination=pg,
                           current_time=datetime.utcnow())


@app.route('/album/', methods=['GET', 'POST'])
def album():
    return render_template('album.html')


@app.route('/time')
def time():
    return str(datetime.now())


@app.route('/item/<asin>')
def product(asin):
    query = Spu.query
    query.equal_to('asin', asin)
    spu = query.first()
    sku_objs = Sku.query\
        .equal_to('spu', spu)\
        .find()
    skus = [sku_obj.dump() for sku_obj in sku_objs]
    return json.dumps({'spu': spu, 'skus': skus})


@sockets.route('/echo')
def echo_socket(ws):
    while True:
        message = ws.receive()
        ws.send(message)
