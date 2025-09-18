from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import uuid, hmac, hashlib, json, threading, requests

app = Flask(__name__)

SECRET_KEY = "flypay_secret"
PAYMENTS = {}

# Page 1: Select Payment Mode
mode_page = """
<!DOCTYPE html>
<html>
<head>
  <title>QuickPay Checkout</title>
</head>
<body style="font-family: Arial; text-align: center; margin-top: 50px;">
  <h1>QuickPay ⚡</h1>
  <h3>Select Payment Mode</h3>
  <p>Payment ID: {{payment_id}}</p>
  <p>Amount: ₹{{amount}}</p>

  <form action="/pay/{{payment_id}}/select" method="post">
    <select name="mode" required>
      <option value="card">💳 Credit/Debit Card</option>
      <option value="upi">📱 UPI</option>
      <option value="netbanking">🏦 Netbanking</option>
      <option value="wallet">👛 Wallet</option>
    </select>
    <br><br>
    <button type="submit">Continue</button>
  </form>
</body>
</html>
"""

# Page 2: Payment details based on mode
details_pages = {
    "card": """
        <h3>Enter Card Details</h3>
        <form method="post">
            Card Number: <input type="text" name="card_no" maxlength="16" required><br><br>
            Expiry: <input type="text" name="expiry" placeholder="MM/YY" required><br><br>
            CVV: <input type="password" name="cvv" maxlength="3" required><br><br>
            <button type="submit" name="status" value="success">✅ Pay</button>
            <button type="submit" name="status" value="failed">❌ Fail</button>
        </form>
    """,
    "upi": """
        <h3>Scan UPI QR</h3>
        <img src="https://via.placeholder.com/200x200.png?text=UPI+QR" alt="UPI QR"><br><br>
        <form method="post">
            <button type="submit" name="status" value="success">✅ Paid</button>
            <button type="submit" name="status" value="failed">❌ Fail</button>
        </form>
    """,
    "netbanking": """
        <h3>Netbanking</h3>
        <form method="post">
            Select Bank:
            <select name="bank" required>
                <option>SBI</option>
                <option>HDFC</option>
                <option>ICICI</option>
                <option>Axis</option>
            </select><br><br>
            <button type="submit" name="status" value="success">✅ Login & Pay</button>
            <button type="submit" name="status" value="failed">❌ Fail</button>
        </form>
    """,
    "wallet": """
        <h3>Wallet Payment</h3>
        <form method="post">
            Wallet ID: <input type="text" name="wallet_id" required><br><br>
            <button type="submit" name="status" value="success">✅ Pay</button>
            <button type="submit" name="status" value="failed">❌ Fail</button>
        </form>
    """
}

@app.route("/create_payment", methods=["POST"])
def create_payment():
    data = request.json
    payment_id = str(uuid.uuid4())
    PAYMENTS[payment_id] = {
        "amount": data.get("amount"),
        "status": "created",
        "callback_url": data.get("callback_url"),
        "mode": None
    }
    return jsonify({
        "payment_id": payment_id,
        "redirect_url": f"http://127.0.0.1:5000/pay/{payment_id}"
    })

# Step 1: Show mode selection page
@app.route("/pay/<payment_id>", methods=["GET"])
def pay(payment_id):
    payment = PAYMENTS.get(payment_id)
    if not payment:
        return "Invalid Payment ID", 404
    return render_template_string(mode_page, payment_id=payment_id, amount=payment["amount"])

# Step 1.5: Save mode and redirect
@app.route("/pay/<payment_id>/select", methods=["POST"])
def select_mode(payment_id):
    mode = request.form.get("mode")
    if payment_id not in PAYMENTS:
        return "Invalid Payment ID", 404
    PAYMENTS[payment_id]["mode"] = mode
    return redirect(url_for("pay_details", payment_id=payment_id, mode=mode))

# Step 2: Show payment details form
@app.route("/pay/<payment_id>/<mode>", methods=["GET", "POST"])
def pay_details(payment_id, mode):
    payment = PAYMENTS.get(payment_id)
    if not payment or payment["mode"] != mode:
        return "Invalid Payment ID or Mode", 404

    if request.method == "GET":
        return f"""
        <html><body style='text-align:center; font-family:Arial; margin-top:50px;'>
        <h1>QuickPay ⚡</h1>
        <p>Amount: ₹{payment['amount']}</p>
        {details_pages[mode]}
        </body></html>
        """

    # POST: simulate payment
    status = request.form.get("status")
    payment["status"] = status

    # Webhook
    def send_webhook():
        payload = {
            "payment_id": payment_id,
            "status": status,
            "amount": payment["amount"],
            "mode": mode
        }
        payload_json = json.dumps(payload)
        signature = hmac.new(SECRET_KEY.encode(), payload_json.encode(), hashlib.sha256).hexdigest()

        try:
            requests.post(
                payment["callback_url"],
                json=payload,
                headers={"X-FlyPay-Signature": signature}
            )
        except Exception as e:
            print("Webhook delivery failed:", e)

    threading.Thread(target=send_webhook).start()

    return f"<h2>QuickPay Payment {status.upper()} via {mode.upper()}</h2>"

if __name__ == "__main__":
    app.run(port=5000, debug=True)