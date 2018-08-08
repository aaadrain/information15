from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request

from info import constants
from info import db
from info.models import News, Category, User
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import profile_blue
from info.utils.common import user_login_data


@profile_blue.route('/other_news_list')
def other_news_list():
    page = request.args.get('p', 1)
    other_id = request.args.get('user_id')
    try:
        page = int(page)
    except Exception as e:
        page = 1
    print(other_id)
    paginate = News.query.filter(News.user_id == other_id).order_by(News.create_time.desc()).paginate(page, 10, False)
    news_items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages
    news_list = []
    for item in news_items:
        news_list.append(item.to_review_dict())
    data = {
        'news_list': news_list,
        'current_page': current_page,
        'total_page': total_page
    }

    return jsonify(errno=RET.OK, errmsg='ok', data=data)


@profile_blue.route('/other_info')
@user_login_data
def other_info():
    user = g.user
    # if not user:
    #     return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
    user_id = request.args.get('id')
    try:
        other = User.query.get(user_id)
    except Exception as e:
        print(e)

    is_followed = False
    if user:
        if other.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    data = {
        'user_info': user.to_dict(),
        'other_info': other.to_dict(),
        'is_followed': is_followed
    }
    return render_template('news/other.html', data=data)


@profile_blue.route('/user_follow')
@user_login_data
def user_follow():
    user = g.user
    page = request.args.get('p', 1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate = user.followed.paginate(page, 10, False)
    followed_users = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    followed_list = []
    for follower in followed_users:
        followed_list.append(follower.to_dict())

    data = {
        'current_page': current_page,
        'total_page': total_page,
        'users': followed_list
    }

    return render_template('news/user_follow.html', data=data)
    pass


@profile_blue.route('/news_list')
@user_login_data
def news_list():
    user = g.user
    page = request.args.get("p", 1)
    print(page)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    print(user.id)
    paginate = News.query.filter(News.user_id == user.id).paginate(page, 2, False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    items_list = []
    for item in items:
        items_list.append(item.to_review_dict())

    data = {
        "news_list": items_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("news/user_news_list.html", data=data)


@profile_blue.route('/news_release', methods=['POST', 'GET'])
@user_login_data
def news_release():
    user = g.user

    if request.method == "GET":
        categories = Category.query.filter(Category.id != 1).all()
        categories_list = []
        for cate in categories:
            categories_list.append(cate.to_dict())

        data = {
            # 'user_info': user.to_dict if user else None,
            'categories': categories
        }
        return render_template('news/user_news_release.html', data=data)

    title = request.form.get('title')
    category_id = request.form.get('category_id')
    print(category_id)
    digest = request.form.get('digest')
    index_image = request.files.get('index_image').read()
    content = request.form.get('content')
    source = '个人发布'
    print(title, category_id)
    print(digest)
    print(index_image)
    print(content)
    if not all([title, source, digest, content, index_image, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    news = News()
    key = storage(index_image)
    index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.title = title
    news.category_id = category_id
    news.content = content
    news.digest = digest
    news.index_image_url = index_image_url
    news.status = 1
    news.source = source
    news.user_id = user.id  # user.id   不写不报错.  但是会过滤不出来.
    db.session.add(news)
    db.session.commit()

    return jsonify(errno=RET.OK, errmsg='ok')


@profile_blue.route('/collection', methods=['POST', 'GET'])
@user_login_data
def user_collection():
    user = g.user
    if not user:
        return redirect('/')
    # if request.method == 'GET':
    #     return render_template('news/user_collection.html', data={'user_info': user.to_dict() if user else None})
    page = request.args.get('p', 1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    # 分页显示的方法 paginate(页码,条目数,是否显示错误路劲)
    paginate = user.collection_news.order_by(News.create_time.desc()).paginate(page, 10, False)
    items = paginate.items  # 总条目数量
    current_page = paginate.page  # 当前页面 从第几页开始
    total_page = paginate.pages  # 总页数

    collections = []
    for collection_news in items:
        collections.append(collection_news)
    data = {
        'collections': collections,
        'current_page': current_page,
        'total_page': total_page,
    }
    return render_template('news/user_collection.html', data=data)


@profile_blue.route('/pass_info', methods=['GET', 'POST'])
@user_login_data
def pass_info():
    user = g.user
    if not user:
        return redirect('/')
    if request.method == 'GET':
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template('news/user_pass_info.html', data=data)

    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')
    print(old_password)
    print(new_password)

    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR, errmsg='原密码错误.')

    user.password = new_password
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='修改成功')


@profile_blue.route('/pic_info', methods=['GET', 'POST'])
@user_login_data
def pic_info():
    user = g.user
    if not user:
        return redirect('/')
    if request.method == 'GET':
        return render_template('news/user_pic_info.html', data={'user_info': user.to_dict()})
    avatar = request.files.get('avatar').read()
    if not avatar:
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    # 再将文件上传到七牛云
    key = storage(avatar)
    user.avatar_url = key
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='操作成功', data=constants.QINIU_DOMIN_PREFIX + key)


@profile_blue.route('/base_info', methods=['GET', 'POST'])
@user_login_data
def base_info():
    user = g.user
    if not user:
        return redirect('/')
    if request.method == 'GET':
        return render_template('news/user_base_info.html', data={'user_info': user.to_dict()})
    nick_name = request.json.get('nick_name')
    signature = request.json.get('signature')
    gender = request.json.get('gender')

    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='操作成功')


    # return render_template('news/user_base_info.html')


@profile_blue.route('/info')
@user_login_data
def get_user_info():
    user = g.user
    if not user:
        return redirect('/')
    # if request.method == 'GET':  # GET请求是请求数据,   post是提交数据
    data = {
        'user_info': user.to_dict() if user else None
    }
    return render_template('news/user.html', data=data)
