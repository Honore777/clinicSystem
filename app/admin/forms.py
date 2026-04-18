from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class CreateStaffForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=255)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField('Phone', validators=[Optional(), Length(max=32)])
    role = SelectField('Role', choices=[('staff','staff'),('manager','manager'),('superadmin','superadmin')], validators=[DataRequired()])
    clinic_id = SelectField('Clinic', coerce=int, validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Create Staff')
