from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from info import create_app, db
from info import models
from info.models import User

config_name = 'develop'
app = create_app(config_name)

manager = Manager(app)
Migrate(app, db)
manager.add_command('mysql', MigrateCommand)


# 创建管理员对象
@manager.option('-n', '--name', dest='name')
@manager.option('-p', '--password', dest='password')
def create_super_user(name, password):
    user = User()
    user.mobile = name
    user.nick_name = name
    user.password = password
    user.is_admin = True

    db.session.add(user)
    db.session.commit()


if __name__ == '__main__':
    manager.run()
