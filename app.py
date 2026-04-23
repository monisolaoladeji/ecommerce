from flask import Flask, jsonify, render_template, request, session
from flask_socketio import SocketIO, emit, join_room


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"
socketio = SocketIO(app, manage_session=False)


PRODUCTS = [
    {
        "id": 1,
        "name": "Classic Sneakers",
        "price": 59.99,
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
    },
    {
        "id": 2,
        "name": "Leather Backpack",
        "price": 84.50,
        "image": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=900&q=80",
    },
    {
        "id": 3,
        "name": "Minimal Watch",
        "price": 120.00,
        "image": "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&w=900&q=80",
    },
    {
        "id": 4,
        "name": "Wireless Headphones",
        "price": 94.99,
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80",
    },
]


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
    return render_template("index.html", products=PRODUCTS, cart=cart_summary())


@app.route("/cart")
def cart_page():
    return render_template("cart.html", cart=cart_summary())


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


@socketio.on("connect")
def handle_connect():
    room = request.sid
    session["cart_room"] = room
    session.modified = True
    join_room(room)
    emit("cart_updated", cart_summary(), to=room)


if __name__ == "__main__":
    socketio.run(app, debug=True)
