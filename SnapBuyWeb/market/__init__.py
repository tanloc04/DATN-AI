from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///snapbuy.db'

app.config['SECRET_KEY'] = 'd56a38d96c8b6ca655497ba6689cfd7ea3d45bd6acf97c4dadfaf006e51ecd36'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

login_manager.login_view = 'login_by_user'

from market import routes
