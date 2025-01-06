from flask_package import app

# from flask_package.models import *

# with app.app_context():
#     products = Product.query.limit(8).all()
#     print("Hi", len(products))

if __name__ == "__main__":
    app.run(debug=True, port=600)
