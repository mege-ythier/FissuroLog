"""Sign-up & log-in forms."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError, AnyOf

sign_up_authorized_mail = ["amandine.mege-ythier@ratp.fr", "test@ratp.com", "amandine_mege@msn.com"]


class SignupForm(FlaskForm):
    """User Sign-up Form."""

    # name = StringField("Name", validators=[DataRequired()])
    email = StringField(
        "Email",
        validators=[
            Email(message="email non valide"),
            DataRequired(),
            # AnyOf(sign_up_authorized_mail)
        ],
    )

    role = StringField(
        "Role",
        validators=[
            DataRequired(),
            AnyOf(["owner", "guest", "admin"])
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=2, message="Select a stronger password."),
        ],
    )
    confirm = PasswordField(
        "Confirm Your Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )

    submit = SubmitField("Register")


class SignupGuestForm(FlaskForm):
    """User Sign-up Form."""

    # name = StringField("Name", validators=[DataRequired()])
    email = StringField(
        "Email",
        validators=[
            Email(message="email non valide"),
            DataRequired(),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=2, message="Select a stronger password."),
        ],
    )
    confirm = PasswordField(
        "Confirm Your Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )

    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    """User Log-in Form."""

    email = StringField("Email", validators=[DataRequired(), Email(message="Enter a valid email.")])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class ChangePasswordForm(FlaskForm):
    new_password = PasswordField('Nouveau mot de passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmez le nouveau mot de passe',
                                     validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Changer de mot de passe')
