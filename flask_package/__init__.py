# from datetime import datetime
from flask import Flask
from logging import DEBUG
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_package.admin_views import setup_admin
from flask_mail import Mail


app = Flask(__name__)
app.secret_key = (
    b"\x02/rf\x9f\xdfy\x98j\r*\xfc\xa2\x0e\xceR\x84\xd2\x85\x0e\x8c\x0e\xe3\xf4"
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../instance/site.db"
app.config["STATIC_FOLDER"] = "static"

app.logger.setLevel(DEBUG)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
setup_admin(app, db)

app.config["MAIL_SERVER"] = "smtp.gmail.com"  # SMTP server
app.config["MAIL_PORT"] = 587  # Port for TLS
app.config["MAIL_USE_TLS"] = True  # Enable TLS
app.config["MAIL_USE_SSL"] = False  # Disable SSL
app.config["MAIL_USERNAME"] = "vegefoods.ecommerce@gmail.com"  # Your email
app.config["MAIL_PASSWORD"] = "jbyn ffta qxwz nges"  # Your email password
app.config["MAIL_DEFAULT_SENDER"] = "aggarwalvishesh0@gmail.com"  # Default sender email

mail = Mail(app)

from flask_package import routes
