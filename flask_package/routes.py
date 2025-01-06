import random
from flask import (
    Flask,
    session,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_mail import Message
from flask_package import app, db, bcrypt, mail
from flask_package.forms import *
from flask_package.models import *
from flask_login import login_user, current_user, logout_user


coupons = {"SAVE50": 50, "FLAT15": 15, "DISCOUNT20": 20}
coupon_applied = None
coupon_discount = 0


@app.route("/index")
@app.route("/home")
@app.route("/")
def index():
    if current_user.is_authenticated:
        user_id = current_user.id

        wishlist_products = (
            db.session.query(Product)
            .join(Wishlist, Wishlist.product_id == Product.product_id)
            .filter(Wishlist.user_id == user_id)
            .all()
        )

        if len(wishlist_products) < 8:
            ordered_products = (
                db.session.query(Product)
                .join(OrderDetail, OrderDetail.product_id == Product.product_id)
                .join(Order, Order.order_id == OrderDetail.order_id)
                .filter(Order.user_id == user_id)
                .distinct()
                .filter(
                    ~Product.product_id.in_([p.product_id for p in wishlist_products])
                )
                .limit(8 - len(wishlist_products))
                .all()
            )
        else:
            ordered_products = []

        total_selected_products = wishlist_products + ordered_products
        remaining_count = 8 - len(total_selected_products)
        if remaining_count > 0:
            random_products = (
                db.session.query(Product)
                .filter(
                    ~Product.product_id.in_(
                        [p.product_id for p in total_selected_products]
                    )
                )
                .order_by(func.random())
                .limit(remaining_count)
                .all()
            )
        else:
            random_products = []

        # Combine all selected products
        personalized_products = wishlist_products + ordered_products + random_products
    else:
        personalized_products = Product.query.order_by(func.random()).limit(8).all()

    return render_template(
        "index.html",
        products=personalized_products,
    )


@app.route("/shop")
def shop():
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category", "all")

    if category == "all":
        products = Product.query.paginate(page=page, per_page=12)
    else:
        products = Product.query.filter_by(category=category).paginate(
            page=page, per_page=12
        )

    return render_template("shop.html", products=products, current_category=category)


@app.route("/search")
def search():
    search = request.args.get("search", "")
    products = []
    if search:
        products = Product.query.filter(Product.name.ilike(f"%{search}%")).paginate(
            page=1, per_page=12
        )

    return render_template("shop.html", products=products, current_category="all")


@app.route("/wishlist")
def wishlist():
    if not current_user.is_authenticated:
        flash("You are required to login first!", "info")
        return redirect(url_for("login"))

    wishlist = (
        db.session.query(Wishlist, Product)
        .join(Product, Wishlist.product_id == Product.product_id)
        .filter(Wishlist.user_id == current_user.id)
        .all()
    )
    return render_template("wishlist.html", cart_items=wishlist)


@app.route("/product/" + "<pdt_nm>".replace(" ", "-"))
def product_page(pdt_nm):
    product = Product.query.filter_by(name=pdt_nm).first()
    if not product:
        return render_template("404.html"), 404

    qty = 0

    if current_user.is_authenticated:
        cart_item = Cart.query.filter_by(
            user_id=current_user.id, product_id=product.product_id
        ).first()
        if cart_item:
            qty = cart_item.quantity

    return render_template(
        "product-single.html",
        product=product,
        quantity=qty,
        products=Product.query.limit(4).all(),
    )


@app.route("/cart", methods=["GET", "POST"])
def cart():
    global coupon_applied, coupons, coupon_discount

    if not current_user.is_authenticated:
        flash("You are required to login first!", "info")
        return redirect(url_for("login"))

    cart_items = (
        db.session.query(Cart, Product)
        .join(Product, Cart.product_id == Product.product_id)
        .filter(Cart.user_id == current_user.id)
        .all()
    )
    total_amount = float(
        sum(
            ((pdt.price - (pdt.price * pdt.discount / 100)) * cart_item.quantity)
            for cart_item, pdt in cart_items
        )
    )

    if request.method == "POST":
        coupoun_tried = request.form["coupon"]
        if coupoun_tried in coupons.keys():
            coupon_applied = coupoun_tried
            coupon_discount = coupons[coupoun_tried]
            flash("Coupon applied successfully!", "success")
        else:
            coupon_applied = None
            coupon_discount = 0
            flash("Invalid Coupon", "warning")

    return render_template(
        "cart.html", cart_items=cart_items, sub_total=float(total_amount)
    )


@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    global cart_count
    if not current_user.is_authenticated:
        return (
            jsonify({"message": "Please log in to add products to your cart!"}),
            401,
            flash("Please login to continue!", "info"),
        )

    existing_cart_item = Cart.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if existing_cart_item:
        existing_cart_item.quantity += 1
    else:
        new_cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(new_cart_item)

    db.session.commit()
    pdt = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    pdt_name = Product.query.filter_by(product_id=product_id).first().name
    cart_count += 1

    return jsonify(
        {
            "message": f"Product {pdt_name} added to cart.\n\n Quantity Add: {pdt.quantity}",
            "cart_count": cart_count,
        }
    ), flash(f"{pdt_name} added successfully!  Quantity : {pdt.quantity}", "success")


@app.route("/remove_from_cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    global cart_count
    if not current_user.is_authenticated:
        return jsonify({"message": "Please log in to add products to your cart!"}), 401

    existing_cart_item = Cart.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    qty = existing_cart_item.quantity

    # if existing_cart_item.quantity > 1:
    #     existing_cart_item.quantity -= 1
    db.session.delete(existing_cart_item)
    db.session.commit()

    pdt = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    pdt_name = Product.query.filter_by(product_id=product_id).first().name
    cart_count -= qty

    return jsonify(
        {
            "message": f"{pdt_name} removed from cart.",
            "cart_count": cart_count,
        }
    ), flash("Product removed successfully!", "success")


@app.route("/update_cart_item", methods=["POST"])
def update_cart_item():
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity"))

    cart_item = Cart.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    if cart_item:
        cart_item.quantity = quantity
        db.session.commit()
        return jsonify({"success": True, "message": "Cart updated successfully."})
    else:
        return jsonify({"success": False, "message": "Item not found in cart."}), 404


@app.route("/subt_from_cart/<int:product_id>", methods=["POST"])
def subt_to_cart(product_id):
    global cart_count
    if not current_user.is_authenticated:
        return jsonify({"message": "Please log in to add products to your cart!"}), 401

    existing_cart_item = Cart.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    stat = True
    if existing_cart_item.quantity > 1:
        existing_cart_item.quantity -= 1
    else:
        db.session.delete(existing_cart_item)
        stat = False
    db.session.commit()
    pdt = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    pdt_name = Product.query.filter_by(product_id=product_id).first().name
    cart_count -= 1

    if stat:
        return jsonify(
            {
                "message": f"{pdt_name} Quantity reduced from cart.\n\n Quantity Left: {pdt.quantity}"
            }
        ), flash(
            f"{pdt_name} Quantity reduced from cart. Quantity Left: {pdt.quantity}",
            "success",
        )
    else:
        return jsonify({"message": f"{pdt_name} removed from cart."}), flash(
            f"{pdt_name} removed from cart.", "success"
        )


@app.route("/add_to_wishlist/<int:product_id>", methods=["POST"])
def add_to_wishlist(product_id):
    if not current_user.is_authenticated:
        return (
            jsonify({"message": "Please log in to add products to your wishlist!"}),
            401,
            flash("Please login to continue!", "info"),
        )

    existing_wishlist_item = Wishlist.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    pdt_name = Product.query.filter_by(product_id=product_id).first().name

    if not existing_wishlist_item:
        new_wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(new_wishlist_item)
        db.session.commit()
        return jsonify({"message": f"{pdt_name} added to wishlist."}), flash(
            f"{pdt_name} added to wishlist.", "success"
        )
    else:
        return jsonify({"message": f"{pdt_name} is already added to wishlist."}), flash(
            f"{pdt_name} is already present in wishlist.", "warning"
        )


@app.route("/remove-from-wishlist/<int:product_id>", methods=["POST"])
def remove_from_wishlist(product_id):

    existing_wishlist_item = Wishlist.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    db.session.delete(existing_wishlist_item)
    db.session.commit()

    pdt = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    pdt_name = Product.query.filter_by(product_id=product_id).first().name

    return jsonify({"message": f"{pdt_name} removed from cart."}), flash(
        "Product removed successfully!", "success"
    )


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    global coupon_discount
    if not current_user.is_authenticated:
        flash("You need to login first.", "info")
        return redirect(url_for("index"))
    cart_items = (
        db.session.query(Cart, Product)
        .join(Product, Cart.product_id == Product.product_id)
        .filter(Cart.user_id == current_user.id)
        .all()
    )
    sub_total = float(
        sum(
            ((pdt.price - (pdt.price * pdt.discount / 100)) * cart_item.quantity)
            for cart_item, pdt in cart_items
        )
    )
    if sub_total > 199:
        delivery = 0
        flash("Congrats! You've got free delivery.", "success")
    else:
        delivery = 20
        flash("For orders above $199, free delivery is available.", "info")

    if request.method == "POST":
        from datetime import datetime

        address = (
            request.form["firstname"]
            + request.form["lastname"]
            + ", "
            + request.form["address1"]
            + ", "
            + request.form["address2"]
            + ", "
            + request.form["address3"]
            + ", "
            + request.form["region"]
            + ", "
            + request.form["address4"]
        )
        order_total = sub_total - coupon_discount + delivery
        orderId = Order.query.count() + 1
        order = Order(
            order_id=orderId,
            user_id=current_user.id,
            total_amount=order_total,
            status="Confirmed",
            address=address,
        )
        db.session.add(order)
        print("Hi")
        for cart_item, pdt in cart_items:
            product = Product.query.filter_by(product_id=cart_item.product_id).first()
            product.stock -= cart_item.quantity
            ord_detail = OrderDetail(
                order_id=orderId,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=(pdt.price - (pdt.price * pdt.discount / 100))
                * cart_item.quantity,
            )
            db.session.add(ord_detail)
        carts = Cart.query.filter_by(user_id=current_user.id)
        for cart in carts:
            db.session.delete(cart)
        db.session.commit()
        print("Bye")
        flash("Order placed successfully!", "success")
        return redirect(url_for("index"))

    user = Users.query.filter_by(id=current_user.id).first()
    return render_template(
        "checkout.html", sub_total=sub_total, user=user, delivery=delivery
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/blog")
def blog():
    return render_template("blog.html")


@app.route("/profile")
def profile():
    if not current_user.is_authenticated:
        flash("You are required to login first!", "info")
        return redirect(url_for("login"))
    return render_template("profile.html", user=current_user, auth_status=True)


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/blog-single")
def blog_single():
    return render_template("blog-single.html")


def send_otp(email):
    otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
    msg = Message(
        "Your OTP for Registration", sender="noreply@yourapp.com", recipients=[email]
    )
    msg.body = f"Your OTP is: {otp}. This OTP will expire in 10 minutes."
    mail.send(msg)
    return otp


@app.route("/verify", methods=["GET", "POST"])
def verification():
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        if str(session.get("otp")) == entered_otp:  # Check OTP
            user_data = session.get("user_data")
            if user_data:
                user = Users(
                    username=user_data["username"],
                    email=user_data["email"],
                    phone=user_data["phone"],
                    address=user_data["address"],
                    password=user_data["password"],
                    image_file="default.jpg",
                )
                db.session.add(user)
                db.session.commit()
                session.pop("otp", None)
                session.pop("user_data", None)
                flash("Account created and verified successfully!", "success")
                return redirect(url_for("login"))
        else:
            flash("Invalid OTP. Please try again.", "danger")

    return render_template("OTP Verify.html", form=VerifyForm())


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()

    if form.validate_on_submit():
        session["otp"] = send_otp(form.email.data)  # Store OTP in session
        session["user_data"] = {
            "username": form.username.data,
            "email": form.email.data,
            "phone": form.phone.data,
            "address": form.address.data,
            "password": bcrypt.generate_password_hash(form.password.data).decode(
                "utf-8"
            ),
        }
        return redirect(url_for("verification"))

    if form.errors:
        flash("Validation Errors: " + str(form.errors), "danger")
        app.logger.error("ValidationError:\n" + str(form.errors))

    return render_template("register.html", title="Register", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login Successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Please enter the correct password.", "danger")

    if form.errors:
        flash("Validation Errors: " + str(form.errors), "danger")
        app.logger.error("ValidationError:\n" + str(form.errors))

    return render_template("login.html", title="Login", form=form)


@app.route("/logout")
def logout():
    logout_user()
    flash("You have successfully logged out.", "info")
    return redirect(url_for("index"))


@app.context_processor
def inject():
    global cart_count, coupon_applied, coupon_discount
    cart_count = 0
    auth_st = False

    if current_user.is_authenticated:
        cart_count = (
            db.session.query(db.func.sum(Cart.quantity))
            .filter_by(user_id=current_user.id)
            .scalar()
            or 0
        )
        auth_st = True
    currentId = 0
    if current_user.is_authenticated:
        currentId = current_user.id
    return {
        "cart_qty": cart_count,
        "auth_status": auth_st,
        "coupon_applied": coupon_applied,
        "coupon_discount": coupon_discount,
        "userId": currentId,
    }


# Admin Routes
@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if request.method == "POST":
        return redirect(url_for("index"))

    if not current_user.is_authenticated or not current_user.username == "Admin":
        return page_not_found(404)
    products = Product.query.all()
    for p in products:
        if p.stock < 20:
            flash(f"Alert! Low Stock left for {p.name}. ", "warning")
    return render_template("admin/dashboard.html")


# @login_required
@app.route("/admin-users")
def admin_users():
    if not current_user.is_authenticated or not current_user.username == "Admin":
        return render_template("404.html"), 404
    users = Users.query.all()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if not current_user.is_authenticated or not current_user.username == "Admin":
        return render_template("404.html"), 404
    user = Users.query.get_or_404(user_id)
    if request.method == "POST":
        user.username = request.form["username"]
        user.email = request.form["email"]
        user.phone = request.form["phone"]
        user.address = request.form["address"]
        db.session.commit()
        flash("User updated successfully!", "success")
        return redirect(url_for("admin_users"))
    return render_template("admin/edit-users.html", user=user)


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_users"))


# CRUD for Products
@app.route("/admin-products")
def admin_products():
    if not current_user.is_authenticated or not current_user.username == "Admin":
        return render_template("404.html"), 404
    products = Product.query.all()
    return render_template("admin/products.html", products=products)


@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not current_user.is_authenticated or not current_user.username == "Admin":
        return render_template("404.html"), 404
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        product.name = request.form["name"]
        product.description = request.form["description"]
        product.price = request.form["price"]
        product.stock = request.form["stock"]
        product.category = request.form["category"]
        product.discount = request.form["discount"]
        image = request.files["image"]
        image_filename = None
        if image:
            import os
            from werkzeug.utils import secure_filename

            UPLOAD_FOLDER = os.path.join(os.getcwd(), "flask_package/static/images")
            app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
            image_filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
            image.save(image_path)
            product.image_file = image_filename
        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/edit_product.html", product=product)


@app.route("/admin/add_product", methods=["GET", "POST"])
def add_product():
    if not current_user.is_authenticated or not current_user.username == "Admin":
        return render_template("404.html"), 404
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        category = request.form["category"]
        price = request.form["price"]
        stock = request.form["stock"]
        discount = request.form["discount"]
        image = request.files["image"]

        if name and category and price and stock and discount:
            image_filename = None
            if image:
                import os
                from werkzeug.utils import secure_filename

                UPLOAD_FOLDER = os.path.join(os.getcwd(), "flask_package/static/images")
                app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
                image_filename = secure_filename(image.filename)
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
                image.save(image_path)
            row_count = Product.query.count()
            product = Product(
                product_id=row_count + 1,
                name=name,
                description=description,
                category=category,
                price=price,
                stock=stock,
                discount=discount,
                image_file=image_filename,
            )
            db.session.add(product)
            db.session.commit()
            flash("Product added successfully!", "success")
            return redirect(url_for("admin_products"))
        else:
            flash("All fields are required.", "danger")

    return render_template("admin/add_product.html")


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!", "success")
    return redirect(url_for("admin_products"))


@app.route("/orders")
def orders():
    if not current_user.is_authenticated:
        flash("Please login first to continue.", "info")

    orders = Order.query.filter_by(user_id=current_user.id)
    return render_template("orders.html", orders=orders)


@app.route("/ordersDetails/<int:order_id>", methods=["GET", "POST"])
def order_details(order_id):
    if not current_user.is_authenticated:
        flash("Please login first to continue.", "info")

    order_items = (
        db.session.query(OrderDetail, Product)
        .join(Product, OrderDetail.product_id == Product.product_id)
        .filter(OrderDetail.order_id == order_id)
        .all()
    )
    return render_template("order-details.html", order_items=order_items, sub_total=0)


@app.route("/admin-orders")
def admin_orders():
    if not current_user.is_authenticated or not current_user.username == "Admin":
        return render_template("404.html"), 404
    orders = Order.query.all()
    return render_template("admin/orders.html", orders=orders)


@app.route("/admin/edit_order/<int:order_id>", methods=["GET", "POST"])
def edit_order(order_id):

    order = Order.query.get_or_404(order_id)
    order_items = OrderDetail.query.filter_by(order_id=order_id).all()

    if request.method == "POST":
        # Update order details
        order.user_id = request.form["user_id"]
        order.total_amount = request.form["total_amount"]
        order.address = request.form["address"]
        order.status = request.form["status"]

        db.session.commit()
        flash(f"Order {order_id} updated successfully!", "success")
        return redirect(url_for("admin_orders"))

    return render_template(
        "admin/edit_orders.html", order=order, order_items=order_items
    )


@app.route("/admin/delete_order_item/<int:order_id>/<int:product_id>", methods=["POST"])
def delete_order_item(order_id, product_id):
    order_item = OrderDetail.query.filter_by(
        order_id=order_id, product_id=product_id
    ).first_or_404()
    order = Order.query.get_or_404(order_id)

    order.total_amount -= order_item.price * order_item.quantity

    db.session.delete(order_item)
    db.session.commit()

    flash(
        f"Item (Product ID: {product_id}) removed from Order #{order_id} and total amount updated!",
        "success",
    )
    return redirect(url_for("edit_order", order_id=order_id))


@app.errorhandler(404)
def page_not_found(e):
    if request.method == "POST":
        return redirect(url_for("index"))
    return render_template("404.html"), 404
