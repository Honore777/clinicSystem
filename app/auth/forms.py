from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Email


class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=200)])
    about = TextAreaField('Tell us about yourself', validators=[Optional(), Length(max=1000)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=200)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class StaffLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=200)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
