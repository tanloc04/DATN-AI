from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import Length, Email, EqualTo, DataRequired, ValidationError, URL
from market.models import Admin, User
from wtforms import FloatField, TextAreaField, IntegerField
from wtforms.validators import NumberRange

class AdminRegisterForm(FlaskForm):
    username = StringField(label='Username', validators=[Length(min=4, max=30), DataRequired()])
    email = StringField(label='Email', validators=[Email(), Length(max=100), DataRequired()])
    password = PasswordField(label='Password', validators=[Length(min=6), DataRequired()])
    confirm_password = PasswordField(label='Confirm Password', validators=[EqualTo('password'), DataRequired()])
    submit = SubmitField(label='Register')

    def validate_username(self, username_to_check):
        admin = Admin.query.filter_by(username=username_to_check.data).first()
        if admin:
            raise ValidationError('Username already exists. Please try a different one.')

    def validate_email(self, email_to_check):
        admin = Admin.query.filter_by(email=email_to_check.data).first()
        if admin:
            raise ValidationError('Email already registered. Try another one.')

class AdminLoginForm(FlaskForm):
    username = StringField(label='Username', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    submit = SubmitField(label='Login')

class ItemForm(FlaskForm):
    name = StringField(label='Product Name', validators=[Length(min=2, max=100), DataRequired()])
    price = FloatField(label='Price', validators=[NumberRange(min=0.01), DataRequired()])
    description = TextAreaField(label='Description', validators=[Length(max=500)])
    image_url = StringField(label='Image URL', validators=[Length(max=255), URL(), DataRequired()])
    submit = SubmitField(label='Save')

    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[
        DataRequired(), Length(min = 2, max = 100, message="Category name must be between 2 and 100 characters!")])
    description = TextAreaField('Description', validators=[Length(max = 500, message = 'Description must be at most 500 characters!')])
    submit = SubmitField('Save')


class UserRegisterForm(FlaskForm):
    username = StringField(label='Username', validators=[Length(min=4, max=30), DataRequired()])
    email = StringField(label='Email', validators=[Email(), Length(max=100), DataRequired()])
    password = PasswordField(label='Password', validators=[Length(min=6), DataRequired()])
    confirm_password = PasswordField(label='Confirm Password', validators=[EqualTo('password'), DataRequired()])
    submit = SubmitField(label='Register')

    def validate_username(self, username_to_check):
        user = User.query.filter_by(username=username_to_check.data).first()
        if user:
            raise ValidationError('Username already exists. Please try a different one.')

    def validate_email(self, email_to_check):
        user = User.query.filter_by(email=email_to_check.data).first()
        if user:
            raise ValidationError('Email already registered. Try another one.')

class UserLoginForm(FlaskForm):
    username = StringField(label='Username', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    submit = SubmitField(label='Login')

class OrderForm(FlaskForm):
    full_name = StringField(label='Full Name', validators=[Length(min=2, max=100), DataRequired()])
    address = TextAreaField(label='Address', validators=[Length(min=5, max=200), DataRequired()])
    phone = StringField(label='Phone Number', validators=[Length(min=10, max=15), DataRequired()])
    submit = SubmitField(label='Submit')

class RatingForm(FlaskForm):
    rating = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    review = TextAreaField('Comment')
    submit = SubmitField('Submit Review')