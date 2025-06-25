from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, Email, EqualTo, DataRequired, ValidationError
from market.models import Admin

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
