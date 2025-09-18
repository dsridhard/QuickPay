#merchant code 

from flask import Flask, request, jsonify
import hmac, hashlib, json, requests

app = Flask(__name__)

# Must match QuickPay PG secret
SECRET_KEY = "QuickPay_secret"

# In-memory orders
ORDERS = {}

# Step 1: Create order & call QuickPay PG
@app.route("/book", methods=["POST"])
def book():
    # Parse JSON data from the request
    data = request.get_json()
    if not data or "amount" not in data:
        return jsonify({"error": "Invalid or missing 'amount' in JSON body"}), 400

    # Extract the amount from the request body
    amount = data["amount"]
    # Order ID for merchant system
    order_id = f"ORD-{len(ORDERS)+1}"
    ORDERS[order_id] = {"amount": amount, "status": "pending"}

    # Call QuickPay PG to create payment
    pg_response = requests.post(
        "http://127.0.0.1:5000/create_payment",
        json={
            "amount": amount,
            "callback_url": "http://127.0.0.1:8000/webhook"
        }
    ).json()

    return jsonify({
        "order_id": order_id,
        "payment_id": pg_response["payment_id"],
        "redirect_url": pg_response["redirect_url"]
    })

# Step 2: Webhook from QuickPay PG
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_data(as_text=True)
    received_sig = request.headers.get("X-QuickPay-Signature")

    # Verify HMAC signature
    expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if received_sig != expected_sig:
        return jsonify({"error": "Invalid signature"}), 400

    data = json.loads(payload)
    payment_id = data["payment_id"]
    status = data["status"]
    mode = data.get("mode")

    # Find merchant order and update
    for order_id, order in ORDERS.items():
        if "payment_id" not in order and order["amount"] == data["amount"]:
            order["payment_id"] = payment_id
            order["status"] = status
            order["mode"] = mode
            break

    print(f"✅ Webhook received: {data}")

    return jsonify({"message": "Webhook processed"}), 200

# Step 3: Check order status
@app.route("/status/<order_id>", methods=["GET"])
def status(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)

if __name__ == "__main__":
    app.run(port=8000, debug=True)