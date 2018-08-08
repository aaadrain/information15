import re

from _datetime import datetime
from flask import current_app
from flask import make_response, jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info import redis_store, db
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.response_code import RET
from . import passport_blue
from info.utils.captcha.captcha import captcha
import random


@passport_blue.route('/image_code')
def image_code():
    # print('请求地址为: ' + request.url)
    code_id = request.args.get('code_id')
    # 获取到前段传递过来的一个随机的验证码
    name, text, image = captcha.generate_captcha()
    # name: 表示图片验证码的名字
    # text: 表示图片验证码的内容 :3345
    # image: 表示的是图片(16jinzhi)
    # print('图片验证码的名字:' + name)
    print('图片验证码的内容:' + text)

    # make_response 表示响应体对象,这个对象的参数表示图片的验证码
    # 从redis_store中度出来的值是byte类型的.   需要设置decode_response来解码.
    redis_store.set('image_code_' + code_id, text, 300)
    resp = make_response(image)
    resp.headers['Content-Type'] = 'image/jpg'
    # 这个是在http协议中,内容格式定义为image/jpg,即可展示出来相应的内容.
    # 告诉系统需要展示的是图片内容.
    return resp


@passport_blue.route('/sms_code', methods=['GET', 'POST'])
def sms_code():
    user = None
    mobile = request.json.get('mobile')
    real_image_code = request.json.get('image_code')
    id_image_code = request.json.get('image_code_id')
    if not all([mobile, real_image_code, id_image_code]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    # print('验证手机好')
    if not re.match('1[3456789]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='请输入正确手机号')
    user = User.query.filter(User.mobile == mobile).first()
    print(user)
    # if not user is None:
    #     return jsonify(error=RET.DATAEXIST, errmsg='此用户已注册,请直接登陆')
    image_code = redis_store.get('image_code_' + id_image_code)
    if not image_code:
        return jsonify(errno=RET.NODATA, errmsg='图片验证码过期')
    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.PARAMERR, errmsg='请输入正确的验证码.')
    redis_store.delete('image_code_' + id_image_code)
    random_sms_code = '%06d' % random.randint(0, 999999)
    redis_store.set('sms_code_' + mobile, random_sms_code, 300)
    print(mobile, real_image_code, id_image_code, random_sms_code)
    # 发送短信
    # statuCode = CCP().send_template_sms(mobile, [random_sms_code, 5], 1)
    # if statuCode != 0:
    #     return jsonify(errno = RET.THIRDERR,errmsg = "短信发送失败")
    return jsonify(errno=RET.OK, errmsg='发送成功.')


@passport_blue.route('/register', methods=['POST', 'GET'])
def register():
    mobile = request.json.get('mobile')
    sms_code = request.json.get('sms_code')
    password = request.json.get('password')
    print(mobile, sms_code, password)
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='请输入正确参数')
    sms_code_redis_store = redis_store.get('sms_code_' + mobile)
    if not sms_code_redis_store:
        return jsonify(errno=RET.PARAMERR, errmsg='短信验证码已经过期')
    if sms_code_redis_store != sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='请输入正确的短信校验码')
    try:
        redis_store.delete('sms_code_' + mobile)
    except Exception as e:
        current_app.logger.error(e)

    user = User()
    user.mobile = mobile
    user.nick_name = mobile
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    # 注册便登陆
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile
    user.last_login = datetime.now()
    return jsonify(errno=RET.OK, errmsg='注册成功')


@passport_blue.route('/login', methods=['POST', 'GET'])
def login():
    mobile = request.json.get('mobile')
    password = request.json.get('password')
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        # 把错误信息存储到log日志里面
        current_app.logger.error(e)
    # print(mobile, password)
    # if not all([mobile, password]):
    #     return jsonify(errno=RET.PARAMERR, errmsg='请输入数据.')
    # user = User.query.filter(mobile == mobile).first()

    if not user:
        return jsonify(errno=RET.NODATA, errmsg='该用户还未注册')

    if not user.check_password(password):
        return jsonify(errno=RET.PWDERR, errmsg='密码错误')
    # 对用户状态进行保持
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile
    # 更新最后登陆的时间
    user.last_login = datetime.now()
    db.session.commit()
    # if user.is_admin:
    #     return redirect(url_for('admin_blue.admin_index'))
    return jsonify(errno=RET.OK, errmsg='登陆成功.')


@passport_blue.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)

    session.pop('is_admin',None)

    return jsonify(errno=RET.OK, errmsg='退出成功')
    pass
