from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Optional, Length, URL, Email


class ClinicOnboardForm(FlaskForm):
    name = StringField('Clinic Name', validators=[DataRequired(), Length(max=255)])
    slug = StringField('Slug', validators=[Optional(), Length(max=255)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    city_id = SelectField('City', coerce=int, validators=[DataRequired()])
    address = StringField('Address', validators=[Optional(), Length(max=512)])
    contact_phone = StringField('Contact Phone', validators=[Optional(), Length(max=32)])
    contact_email = StringField('Contact Email', validators=[Optional(), Email(), Length(max=255)])
    website = StringField('Website', validators=[Optional(), URL(), Length(max=512)])
    services = TextAreaField('Services (comma separated)', validators=[Optional(), Length(max=2000)])
    latitude = StringField('Latitude', validators=[Optional()])
    longitude = StringField('Longitude', validators=[Optional()])
    # Optional clinic admin fields — if provided we'll create a staff user for the clinic
    admin_name = StringField('Administrator name', validators=[Optional(), Length(max=255)])
    admin_email = StringField('Administrator email', validators=[Optional(), Email(), Length(max=255)])
    admin_password = PasswordField('Administrator password', validators=[Optional(), Length(min=6, max=128)])
    submit = SubmitField('Create Clinic')


class ClinicStaffForm(FlaskForm):
        """Form used by a clinic admin to create staff users for their clinic.

        Notes:
        - Clinic is implied from the logged-in staff (g.staff.clinic_id) so we
            don't expose a clinic selector here.
        - Role is fixed to 'staff' for simplicity; superadmin UI can still
            create managers/superadmins in the admin blueprint.
        """

        name = StringField('Name', validators=[DataRequired(), Length(max=255)])
        email = StringField('Email', validators=[DataRequired(), Email(), Length(max=255)])
        phone = StringField('Phone', validators=[Optional(), Length(max=32)])
        password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])
        submit = SubmitField('Create User')
