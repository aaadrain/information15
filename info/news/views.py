from flask import abort, jsonify
from flask import current_app
from flask import g
from flask import render_template
from flask import request
from flask import session

from info import db
from info.models import User, News, Comment, CommentLike
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blue



@news_blue.route('/followed_user', methods=["POST", "GET"])
@user_login_data
def followed_user():
    # 已经登陆的用户
    login_user = g.user
    if not login_user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')
    user_id = request.json.get('user_id')

    # 作者用户
    author_user = User.query.filter(User.id == user_id).first()
    action = request.json.get('action')

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')
    if action not in ('follow','unfollow'):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不对')

    if action == 'follow':
        if author_user.followers.filter(User.id ==login_user.id).count()>0:
            return jsonify(errno=RET.DATAEXIST,errmsg='当前已经关注')
        author_user.followers.append(login_user)
    else:
        if author_user.followers.filter(User.id ==login_user.id).count()>0:
            author_user.followers.remove(login_user)

    db.session.commit()
    return jsonify(errno=RET.OK,errmsg='操作成功')


@news_blue.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):
    user = g.user
    # 获取当前新闻的所有评论
    '''
    通过新闻id就可以查到新闻评论列表.
    '''
    comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    comments_list = []
    '''
    获取到新闻详情页面评论点赞的数据
    '''
    commentLike_list = []
    comment_like_ids = []
    if user:
        commentLike_list = CommentLike.query.filter(CommentLike.user_id == user.id).all()
        comment_like_ids = [comment_like.comment_id for comment_like in commentLike_list]

    for comment in comments:
        comment_dict = comment.to_dict()
        comment_dict['is_like'] = False
        # comment_like_ids:所有的评论点赞id
        if comment.id in comment_like_ids:
            comment_dict['is_like'] = True
        comments_list.append(comment_dict)

    '''
    首页右边的热门新闻排行
    '''
    news_rank = News.query.order_by(News.clicks.desc()).limit(10)
    news_rank_list = []
    for news in news_rank:
        news_rank_list.append(news.to_dict())

    '''
    获取新闻的详细数据
    '''
    news = News.query.get(news_id)

    # 判断是否收藏该新闻,默认值为false
    is_collected = False

    # 判断登录的用户是否关注当前新闻作者
    is_followed = False

    # 判断用户是否收藏过该新闻
    if user and news.user:
        if news in g.user.collection_news:
            is_collected = True
        if news.user.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    data = {
        'news': news.to_dict(),
        'click_news_list': news_rank_list,
        'user_info': user.to_dict() if user else None,
        'is_collected': is_collected,
        'is_followed': is_followed,
        'comments': comments_list
    }

    # 在详情页面继承父类的模板的时候需要将data也传过去,  否则会报错.
    return render_template('news/detail.html', data=data)


# 运行测试，g 变量是一个应用上下文变量，类似于一个全局变量，
# 但是 g 变量里面的保存的值是相对于每次请求的，不同的请求，g 变量里面
# 保存的值是不同的，所以同一次请求，可以使用 g 变量来保存值用于进行函数的传递。


@news_blue.route('/news_collect', methods=["POST"])
@user_login_data
def news_collect():
    news_id = request.json.get('news_id')
    # 前端用户传过来的动作,收藏新闻或者取消收藏新闻.
    action = request.json.get('action')
    user = g.user
    news = News.query.get(news_id)
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

    if action == 'collect':
        user.collection_news.append(news)
    else:
        user.collection_news.remove(news)

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='收藏成功')


@news_blue.route('/news_comment', methods=['POST', 'GET'])
@user_login_data
def news_comment():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登陆')
    news_id = request.json.get('news_id')
    comment_str = request.json.get('comment')
    parent_id = request.json.get('parent_id')
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不足')
    '''
    用户登陆才能评论
    评论前需要知道新闻id,-----
    评论之后,只要把评论信息存到数据库,为了方便下次用户可以看到评论
    '''
    news = News.query.get(news_id)
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news.id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id
    db.session.add(comment)
    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='评论成功', data=comment.to_dict())


@news_blue.route('/comment_like', methods=['POST'])
@user_login_data
def comment_like():
    user = g.user
    '''
    1.点赞必须用户登录
    2.点赞是针对当前评论,有评论才需要点赞,首先查询评论点赞
    3.查询评论,在查询点赞评论的时候,需要根据当前的评论id,
    和用户id进行查询
    4.查询出来点赞的评论之后,需要进行判断,当前这条评论是否有值
    如果没有值才可以进行点赞
    '''
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='请登录')
    comment_id = request.json.get('comment_id')
    news_id = request.json.get('news_id')
    action = request.json.get('action')

    comment = Comment.query.get(comment_id)
    if not all([comment_id, news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')
    if not comment_id:
        return jsonify(errno=RET.PARAMERR, errmsg='没有评论')

    comment_like = CommentLike().query.filter(CommentLike.comment_id == comment_id,
                                              CommentLike.user_id == user.id).first()

    if action == 'add':
        # comment_like = CommentLike().query.filter(CommentLike.comment_id == comment_id,CommentLike.user_id == user.id).first()
        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            comment.like_count += 1

    else:
        # comment_like = CommentLike().query.filter(CommentLike.comment_id == comment_id,CommentLike.user_id == user.id).first()
        if comment_like:
            db.session.delete(comment_like)
            comment.like_count -= 1

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg='操作成功.')
