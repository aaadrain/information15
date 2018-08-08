from flask import g
from flask import request, jsonify
from flask import session

from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import index_blue
from flask import render_template, current_app


@index_blue.route('/')
def index():
    user_id = session.get('user_id')
    user = None
    if user_id:
        user = User.query.get(user_id)
    '''
    获取到右边的热门点击新闻
    获取了十条热门新闻
    '''
    news = News.query.order_by(News.clicks.desc()).limit(10)
    news_list = []
    for news_mode in news:
        news_list.append(news_mode.to_dict())

    '''
    获取到上面的新闻分类的标题
    '''
    categories = Category.query.all()
    category_list = []
    for category in categories:
        category_list.append(category.to_dict())

    data = {
        'user_info': user.to_dict() if user else None,
        'click_news_list': news_list,
        'categories': category_list
    }
    return render_template('news/index.html', data=data)


'''
current_app:表示app的代理对象,直接代理app
'''

@index_blue.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')


@index_blue.route('/news_list')
@user_login_data
def news_list():
    page = request.args.get('page', 1)
    cid = request.args.get('cid', 1)
    per_page = request.args.get('per_page', 10)
    try:
        page = int(page)
        cid = int(cid)
        per_page = int(per_page)
    except Exception as e:
        page = 1
        cid = 1
        per_page = 10
    filter = [News.status == 0]
    # filter = []
    if cid != 1:
        filter.append(News.category_id == cid)
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, per_page, False)
    # 获取当前页面需要展示的数据
    items = paginate.items
    # 表示当前页面
    current_page = paginate.page
    # 表示总页数
    total_page = paginate.pages
    news_list = []
    for item in items:
        news_list.append(item.to_dict())
    data = {
        'current_page': current_page,
        'total_page': total_page,
        'news_dict_li': news_list,
        'user_info':g.user.to_dict() if g.user else None,
    }
    return jsonify(errno=RET.OK, errmsg='ok', data=data)
    pass
