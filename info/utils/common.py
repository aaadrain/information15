# 自定义过滤器
import functools

from flask import g
from flask import session


def do_index(index):
    if index == 0:
        return 'first'
    elif index == 1:
        return 'second'
    elif index == 2:
        return 'third'
    else:
        return ''


# 这个是装饰器 全局作用.
def user_login_data(f):
    @functools.wraps(f)  # functools.wraps =
    def wrapper(*args, **kwargs):
        # 如果session里面有值,说明我已经登陆了,
        user_id = session.get('user_id')
        # 通过id获得用户信息
        user = None
        if user_id:
            from info.models import User
            user = User.query.get(user_id)

        g.user = user
        return f(*args,**kwargs)
    return wrapper

    # user_id = session.get('user_id')
    # # 获取用户信息
    # user = None
    # if user_id:
    #     try:
    #         user = User.query.get(user_id)
    #     except Exception as e:
    #         current_app.logger.error(e)