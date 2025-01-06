from flask_package import db, login_manager
from flask_login import UserMixin
from sqlalchemy.sql import func

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    image_file = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    address = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"User('{self.username}','{self.email}', '{self.phone}')"


class Product(db.Model):
    __tablename__ = "Products"

    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    image_file = db.Column(db.String(100), nullable=False)
    discount = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"Product('{self.name}','{self.price}','{self.stock}')"


class Order(db.Model):
    __tablename__ = "Orders"  # Ensure this matches your table name

    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False,default=func.now())
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False) # confirmed, dispatched, delivered
    address = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<Order(order_id={self.order_id}, user_id={self.user_id}, total_amount={self.total_amount}, status={self.status})>"


class OrderDetail(db.Model):
    __tablename__ = "OrderDetails"  # Matches your table name

    order_id = db.Column(
        db.Integer, db.ForeignKey("Orders.order_id"), primary_key=True, nullable=False
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("Products.product_id"),
        primary_key=True,
        nullable=False,
    )
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f"<OrderDetail(order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity}, price={self.price})>"


class Cart(db.Model):
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, primary_key=True
    )
    product_id = db.Column(db.Integer, nullable=False, primary_key=True)
    quantity = db.Column(db.Integer, default=1)


class Wishlist(db.Model):
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, primary_key=True
    )
    product_id = db.Column(db.Integer, nullable=False, primary_key=True)
