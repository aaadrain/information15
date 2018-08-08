from flask import Blueprint

profile_blue = Blueprint('user',__name__,url_prefix='/user')

from . import views