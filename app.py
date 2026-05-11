import os
import random
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from pymongo import MongoClient


load_dotenv()

MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://monisola:portfolio2026@cluster0.eaer1cp.mongodb.net/?appName=Cluster0"
)
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "ecommerce_db")
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
products_collection = mongo_db["products"]

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-this-in-production")
socketio = SocketIO(app, manage_session=False)

CORS(app)


DEFAULT_PRODUCTS = [
    {
        "id": 1,
        "name": "Classic Sneakers",
        "price": 59.99,
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
        "category": "Footwear",
        "description": "Timeless design meets comfort. Perfect for everyday wear.",
    },
    {
        "id": 2,
        "name": "Leather Backpack",
        "price": 84.50,
        "image": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=900&q=80",
        "category": "Bags",
        "description": "Premium leather backpack with multiple compartments for your essentials.",
    },
    {
        "id": 3,
        "name": "Minimal Watch",
        "price": 120.00,
        "image": "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&w=900&q=80",
        "category": "Accessories",
        "description": "Elegant and minimalist design. The perfect accessory for any outfit.",
    },
    {
        "id": 4,
        "name": "Wireless Headphones",
        "price": 94.99,
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80",
        "category": "Electronics",
        "description": "Crystal clear sound with noise cancellation. Experience audio like never before.",
    },
    {
        "id": 5,
        "name": "Denim Jacket",
        "price": 79.99,
        "image": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?auto=format&fit=crop&w=900&q=80",
        "category": "Clothing",
        "description": "Classic denim jacket with a modern fit. A wardrobe staple.",
    },
    {
        "id": 6,
        "name": "Smart Watch",
        "price": 199.99,
        "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80",
        "category": "Electronics",
        "description": "Stay connected with this feature-packed smartwatch.",
    },
]


def init_db():
    products_collection.create_index("id", unique=True)
    if products_collection.count_documents({}) == 0:
        products_collection.insert_many(DEFAULT_PRODUCTS)


def load_products():
    products = list(products_collection.find({}, {"_id": 0}))
    return [dict(product) for product in products]


init_db()
PRODUCTS = load_products()


def get_cart():
    return session.setdefault("cart", {})


def build_cart_items():
    cart = get_cart()
    items = []
    total = 0.0

    for product in PRODUCTS:
        quantity = cart.get(str(product["id"]), 0)
        if quantity <= 0:
            continue

        subtotal = round(product["price"] * quantity, 2)
        total += subtotal
        items.append(
            {
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "image": product["image"],
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )

    return items, round(total, 2)


def cart_summary():
    items, total = build_cart_items()
    count = sum(item["quantity"] for item in items)
    return {"items": items, "total": total, "count": count}


def broadcast_cart_update():
    room = session.get("cart_room")
    if room:
        socketio.emit("cart_updated", cart_summary(), to=room, namespace="/")


@app.route("/")
def index():
    search_query = request.args.get("q", "")
    filtered_products = PRODUCTS
    if search_query:
        search_query_lower = search_query.lower()
        filtered_products = [
            p for p in PRODUCTS
            if search_query_lower in p["name"].lower()
            or search_query_lower in p["category"].lower()
            or search_query_lower in p["description"].lower()
        ]
    return render_template("index.html", products=filtered_products, cart=cart_summary(), search_query=search_query)


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return render_template("404.html"), 404
    return render_template("product.html", product=product, cart=cart_summary())


@app.route("/cart")
def cart_page():
    return render_template("cart.html", cart=cart_summary())


@app.route("/checkout")
def checkout_page():
    return render_template("checkout.html", cart=cart_summary())


@app.route("/api/cart", methods=["GET"])
def get_cart_data():
    return jsonify(cart_summary())


@app.route("/api/cart/add", methods=["POST"])
def add_to_cart():
    payload = request.get_json(silent=True) or {}
    product_id = str(payload.get("product_id", ""))
    cart = get_cart()

    if product_id not in {str(product["id"]) for product in PRODUCTS}:
        return jsonify({"error": "Product not found."}), 404

    cart[product_id] = cart.get(product_id, 0) + 1
    session["cart"] = cart
    session.modified = True
    broadcast_cart_update()
    return jsonify(cart_summary())


@app.route("/api/cart/update", methods=["POST"])
def update_cart():
    payload = request.get_json(silent=True) or {}
    product_id = str(payload.get("product_id", ""))
    quantity = int(payload.get("quantity", 1))
    cart = get_cart()

    if product_id not in {str(product["id"]) for product in PRODUCTS}:
        return jsonify({"error": "Product not found."}), 404

    if quantity <= 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = quantity

    session["cart"] = cart
    session.modified = True
    broadcast_cart_update()
    return jsonify(cart_summary())


@app.route("/api/cart/clear", methods=["POST"])
def clear_cart():
    session["cart"] = {}
    session.modified = True
    broadcast_cart_update()
    return jsonify(cart_summary())


@app.route("/api/ai/recommend", methods=["POST"])
def ai_recommend():
    payload = request.get_json(silent=True) or {}
    query = payload.get("query", "")
    
    if not query:
        random_products = random.sample(PRODUCTS, min(3, len(PRODUCTS)))
        return jsonify({"recommendations": random_products, "message": "Here are some popular products!"})
    
    query_lower = query.lower()
    relevant_products = [
        p for p in PRODUCTS
        if query_lower in p["name"].lower()
        or query_lower in p["category"].lower()
        or query_lower in p["description"].lower()
    ]
    
    if not relevant_products:
        relevant_products = random.sample(PRODUCTS, min(3, len(PRODUCTS)))
        message = f"Couldn't find exact matches for '{query}'. Here are some suggestions!"
    else:
        message = f"Here are some products related to '{query}'!"
    
    return jsonify({
        "recommendations": relevant_products[:3],
        "message": message
    })


@app.route("/api/checkout", methods=["POST"])
def mock_checkout():
    payload = request.get_json(silent=True) or {}
    order_id = f"ORD-{random.randint(10000, 99999)}"
    session["cart"] = {}
    session.modified = True
    broadcast_cart_update()
    return jsonify({
        "success": True,
        "order_id": order_id,
        "message": "Order placed successfully! This is a mock checkout."
    })


@socketio.on("connect")
def handle_connect():
    room = request.sid
    session["cart_room"] = room
    session.modified = True
    join_room(room)
    emit("cart_updated", cart_summary(), to=room)


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
