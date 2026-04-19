from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, Email


class PatientProfileForm(FlaskForm):
    name = StringField('Full name', validators=[DataRequired(), Length(max=255)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=32)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=255)])
    preferred_language = SelectField('Preferred language', choices=[('rw', 'Kinyarwanda'), ('en', 'English')], default='rw')
    city_id = SelectField('City', coerce=int, choices=[], validators=[Optional()])
    submit = SubmitField('Save profile')
