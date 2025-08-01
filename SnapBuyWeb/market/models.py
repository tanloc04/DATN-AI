import datetime
from market import db, login_manager
from market import bcrypt
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Item(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(length=100))
    price = db.Column(db.Numeric(10, 2))
    description = db.Column(db.Text())
    image_url = db.Column(db.String(length=255))
    created_at = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    brand_id = db.Column(
        db.Integer,
        db.ForeignKey('brand.id', name='fk_item_brand'),
        nullable=True
    )
    item_tag = db.Table('item_tag',
                        db.Column('item_id', db.Integer, db.ForeignKey('item.id')),
                        db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                        )
    tags = db.relationship('Tag', secondary=item_tag, backref='items')

    def __repr__(self):
        return f'<Item {self.name}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=100), unique=True, nullable=False)
    items = db.relationship('Item', backref='brand', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(length=30), nullable=False, unique=True)
    email = db.Column(db.String(length=50), nullable=False, unique=True)
    password_hash = db.Column(db.String(length=60), nullable=False)
    is_active = db.Column(db.Boolean(), default=True)
    role = db.Column(db.String(length=20), default='user')
    items = db.relationship('Item', backref='owner', lazy=True)
    created_at = db.Column(db.DateTime(), default=datetime.datetime.utcnow)

    @property
    def password(self):
        raise AttributeError("Password is write-only.")

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    total_price = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='processing')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='orders')
    item = db.relationship('Item', backref='orders')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    items = db.relationship('Item', backref='category', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)

    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='ratings')
    item = db.relationship('Item', backref='ratings')
    order = db.relationship('Order', backref=db.backref('rating', uselist=False))


class UserHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)

    interaction_type = db.Column(db.String(50), nullable=False, default="view")
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='histories')
    item = db.relationship('Item', backref='histories')

    def __repr__(self):
        return f"<UserHistory {self.user_id} -> {self.item_id} [{self.interaction_type}]>"
