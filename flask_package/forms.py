from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    EqualTo,
    ValidationError,
    number_range,
)

from flask import flash
from flask_package.models import Users


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=2, max=20)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField(
        "Phone", validators=[DataRequired(), Length(min=10, max=10)]
    )
    address = StringField("Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Sign Up")

    def validate_username(self, username):
        user = Users.query.filter_by(username=username.data).first()
        if user:
            # flash("Username already exists.","info")
            raise ValidationError(message="Username already exists.")

    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if user:
            # flash("Email already exists.","info")
            raise ValidationError(message="Email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    # remember = BooleanField('Remember Me')
    submit = SubmitField("Log In")
    
    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError(message="Email not registered.")


class VerifyForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Verify")