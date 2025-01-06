from flask_admin import Admin
from flask import redirect, url_for
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user


class MyAdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(
            current_user, "is_admin", False
        )

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login"))


def setup_admin(app, db):
    admin = Admin(app, name="Admin Panel", template_mode="bootstrap4")
    from flask_package.models import Users, Product,Order,OrderDetail

    admin.add_view(MyAdminView(Users, db.session))
    admin.add_view(MyAdminView(Product, db.session))
    admin.add_view(MyAdminView(Order, db.session))
    admin.add_view(MyAdminView(OrderDetail, db.session))
