from flask import current_app
from flask import g, jsonify
from flask import session

from info import constants
from info import db
from info.models import User, News, Category
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blue
from flask import render_template, redirect, url_for, request
from info.utils.common import user_login_data
import time
from datetime import datetime, timedelta


@admin_blue.route('/add_category', methods=['POST', 'GET'])
def add_category():
    category_name = request.json.get('name')
    category_id = request.json.get('id')

    if category_id:
        if not Category.query.filter(Category.id.contains(category_id)).first():
            return jsonify(errno=RET.PARAMERR,errmsg='id输入有误')
        if not category_name:
            return jsonify(errno=RET.PARAMERR,errmsg='请输入新类目')
        if Category.query.filter(Category.name.contains(category_name)).first():
            return jsonify(errno=RET.PARAMERR,errmsg='新条目已经存在')

        category = Category.query.filter(Category.id == category_id).first()
        category.name = category_name

    else:
        category = Category()
        category.name = category_name
        db.session.add(category)

    db.session.commit()
    return jsonify(errno=RET.OK,errmsg='添加成功')
    pass


@admin_blue.route('/news_type')
def news_type():
    categories = Category.query.filter(Category.id != 1).all()
    category_list = []
    for cate in categories:
        category_list.append(cate.to_dict())

    data = {
        'categories': category_list,
    }
    return render_template('admin/news_type.html', data=data)
    pass


@admin_blue.route('/news_edit_detail', methods=['GET', 'POST'])
def news_edit_detail():
    if request.method == 'GET':
        news_id = request.args.get('news_id')
        news = News.query.get(news_id)

        category_list = []
        categories = Category.query.filter(Category.id != 1).all()
        for category in categories:
            category_list.append(category.to_dict())

        data = {
            'news': news.to_dict(),
            'category_list': category_list,
        }
        return render_template('admin/news_edit_detail.html', data=data)

    news_id = request.form.get('news_id')
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    title = request.form.get('title')
    digest = request.form.get('digest')
    content = request.form.get('content')
    index_image = request.files.get('index_image')
    category_id = request.form.get('category_id')

    print(news_id)
    print(title)
    print(digest)
    print(content)
    print(index_image)
    print(category_id)
    if not all([news_id, title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    if not news:
        return jsonify(errno=RET.NODATA, errmsg='未查询到新闻数据')
    if index_image:
        index_image = index_image.read()

        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="第三方系统错误")
        index_image_url = constants.QINIU_DOMIN_PREFIX + key

    if index_image:
        news.index_image_url = index_image_url

    news.title = title
    news.digest = digest
    news.content = content

    news.category_id = category_id
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='操作成功')


@admin_blue.route('/news_edit')
def news_edit():
    '''
    以分页的形式按新闻创建时间倒序展示出新闻数据
    可以使用关键这这对新闻标题进行搜索
    点击编辑进入编辑详情页面
    '''
    page = request.args.get('p', 1)
    keywords = request.args.get('keywords', '')

    try:
        page = int(page)
    except Exception as e:
        page = 1

    filter = [News.status == 0]
    if keywords:
        filter.append(News.title.contains(keywords))

    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_list = []
    for news in items:
        news_list.append(news.to_dict())

    data = {
        'current_page': current_page,
        'total_page': total_page,
        'news_list': news_list
    }

    return render_template('admin/news_edit.html', data=data)


@admin_blue.route('/news_review_detail', methods=['POST', 'GET'])
def news_review_detail():
    news_id = request.args.get('news_id')
    if request.method == 'GET':
        if not news_id:
            return render_template('admin/news_review_detail.html', data={'errmsg': '未查询到此新闻'})
        news = News.query.get(news_id)
        if not news:
            return render_template('admin/news_review_detail.html', data={'errmsg': '未查询到此新闻'})

        return render_template('admin/news_review_detail.html', data={'news': news.to_dict()})

    action = request.json.get('action')
    news_id = request.json.get('news_id')
    reason = request.json.get('reason')

    if not all([action, news_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    news = News.query.get(news_id)
    if not action == 'reject':
        news.status = 0
    else:
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg='没有写未通过的理由')
        news.reason = reason
        news.status = -1
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='OK')


@admin_blue.route('/news_review')
def news_review():
    '''
    以分页的形式按新闻创建时间倒序展示出待审核的新闻数据
    可以使用关键这这对新闻标题进行搜索
    点击审核进入审核详情页面(对新闻只能查看不能编辑)
    审核不通过需要写明不通过原因
    '''
    page = request.args.get('p', 1)
    keywords = request.args.get('keywords', '')
    try:
        page = int(page)
    except Exception as e:
        page = 1
    filter = [News.status != 0]
    if keywords:
        filter.append(News.title.contains(keywords))  # contains() 包含.
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    news_list = []
    for news in items:
        news_list.append(news.to_review_dict())
    data = {
        'news_list': news_list,
        'current_page': current_page,
        'total_page': total_page,
    }
    return render_template('admin/news_review.html', data=data)


@admin_blue.route('/user_list')
def user_list():
    users = []
    current_page = 1
    total_page = 1
    page = request.args.get('p', 1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page, 10, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    for user in items:
        users.append(user.to_admin_dict())

    data = {
        'current_page': current_page,
        'total_page': total_page,
        'users': users
    }
    return render_template('admin/user_list.html', data=data)
    pass


@admin_blue.route("/user_count")
def user_count():
    # 总人数
    total_count = 0
    # 每个月新增的人数
    mon_count = 0
    # 每天新增加的人数
    day_count = 0
    # 获取到总人数
    total_count = User.query.filter(User.is_admin == False).count()
    # 2018-08-01 00:00:00
    t = time.localtime()
    mon_begin = "%d-%02d-01" % (t.tm_year, t.tm_mon)
    mon_begin_date = datetime.strptime(mon_begin, '%Y-%m-%d')
    # datetime.strptime(输出的时间,格式)

    # 获取到本月的新增人数
    mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()

    # 2018-08-01 00:00:00
    t = time.localtime()
    day_begin = "%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)
    day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')

    # now_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')

    # 获取到jintian的人数
    day_count = User.query.filter(User.is_admin == False, User.create_time >= day_begin_date).count()
    t = time.localtime()
    today_begin = "%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)
    today_begin_date = datetime.strptime(today_begin, '%Y-%m-%d')
    active_time = []
    active_count = []

    for i in range(0, 30):
        begin_date = today_begin_date - timedelta(days=i)
        end_date = today_begin_date - timedelta(days=(i - 1))
        # active_time.append(begin_date.strftime('%Y-%m-%d'))

        count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                  User.last_login < end_date).count()
        active_count.append(count)
        active_time.append(begin_date.strftime('%Y-%m-%d'))
    active_time.reverse()
    active_count.reverse()
    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        'active_count': active_count,
        'active_time': active_time
    }

    return render_template("admin/user_count.html", data=data)


@admin_blue.route("/index")
@user_login_data
def admin_index():
    user = g.user
    return render_template("admin/index.html", user=user.to_dict() if user else None)


@admin_blue.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin/login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter(User.mobile == username, User.is_admin == True).first()

    if not user:
        return render_template("admin/login.html", errmsg="没有这个用户")

    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="密码错误")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = user.is_admin

    # 如果登陆成功,需要调到主页面
    return redirect(url_for("admin.admin_index"))
