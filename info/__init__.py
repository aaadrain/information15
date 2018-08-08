import logging
from logging.handlers import RotatingFileHandler

import redis
from flask import Flask
from flask import g
from flask import render_template
from flask.ext.session import Session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.wtf import CSRFProtect
from flask.ext.wtf.csrf import generate_csrf

from config import config_maps

# 设置日志的记录等级
from info.utils.common import user_login_data

logging.basicConfig(level=logging.DEBUG)  # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)

db = SQLAlchemy()
redis_store = None


def create_app(class_name):
    app = Flask(__name__)
    config_class = config_maps.get(class_name)
    app.config.from_object(config_class)  # 数据库最先加载
    db.init_app(app)
    global redis_store
    redis_store = redis.StrictRedis(host='127.0.0.1', port=6379, decode_responses=True)
    Session(app)
    CSRFProtect(app)

    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie('csrf_token', csrf_token)
        return response

    @app.errorhandler(404)
    @user_login_data
    def page_not_found(_):
        user = g.user
        data = {
            'user_info': user.to_dict() if user else None
        }
        return render_template('news/404.html', data=data)

    from info.utils.common import do_index
    # 添加一个模板过滤器
    app.add_template_filter(do_index, 'indexClass')

    from info.admin import admin_blue
    app.register_blueprint(admin_blue)

    from info.user import profile_blue
    app.register_blueprint(profile_blue)

    from info.index import index_blue
    app.register_blueprint(index_blue)  # 要注册方法.

    from info.passport import passport_blue
    app.register_blueprint(passport_blue)  # 要注册方法.

    from info.news import news_blue
    app.register_blueprint(news_blue)

    return app
