from flask import Flask, request, jsonify, render_template_string, send_file
import uuid, hmac, hashlib, json, threading, requests, io, qrcode, datetime

app = Flask(__name__)

SECRET_KEY = "flypay_secret"
PAYMENTS = {}
SESSION_TIMEOUT = 5  # minutes

mode_page = """
<!DOCTYPE html>
<html>
<head>
  <title>QuickPay Checkout</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      display: flex;
      min-height: 100vh;
      background: #fafafa;
    }

    .sidebar {
      background: #f4f4f4;
      width: 250px;
      padding: 20px;
      box-shadow: 2px 0 5px rgba(0,0,0,0.1);
    }

    .sidebar h1 {
      text-align: center;
      margin-bottom: 10px;
    }

    .sidebar p {
      text-align: center;
      font-size: 14px;
      margin: 4px 0;
    }

    .payment-modes {
      list-style: none;
      padding: 0;
      margin-top: 20px;
    }

    .payment-modes li {
      background: white;
      margin-bottom: 10px;
      border-radius: 8px;
      border: 1px solid #ddd;
      cursor: pointer;
      text-align: center;
      transition: background 0.2s;
    }

    .payment-modes li:hover {
      background: #eaeaea;
    }

    input[type="radio"] {
      display: none;
    }

    input[type="radio"]:checked + label {
      background-color: #007bff;
      color: white;
      border-radius: 8px;
    }

    label {
      display: block;
      padding: 12px;
      cursor: pointer;
    }

    .content {
      flex: 1;
      padding: 40px;
      background: white;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
    }

    .content h3 { margin-top: 0; }

    .content form input,
    .content form select {
      width: 250px;
      padding: 8px;
      margin: 6px 0;
      border: 1px solid #ccc;
      border-radius: 6px;
    }

    .content button {
      background-color: #007bff;
      color: white;
      padding: 10px 16px;
      margin: 6px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }

    .content button:hover {
      background-color: #0056b3;
    }

    .timer {
      font-size: 14px;
      margin-bottom: 10px;
      color: red;
    }
  </style>
</head>
<body>
  <div class="sidebar">
    <h1>QuickPay ⚡</h1>
    <p>Payment ID: {{payment_id}}</p>
    <p style='font-bold'>Amount: ₹{{amount}}</p>
    <p class="timer" id="timer"></p>

    <ul class="payment-modes">
      <li><input type="radio" id="card" name="mode" onclick="showDetails('card')" required><label for="card">💳 Card</label></li>
      <li><input type="radio" id="upi" name="mode" onclick="showDetails('upi')"><label for="upi">📱 UPI</label></li>
      <li><input type="radio" id="netbanking" name="mode" onclick="showDetails('netbanking')"><label for="netbanking">🏦 Netbanking</label></li>
      <li><input type="radio" id="wallet" name="mode" onclick="showDetails('wallet')"><label for="wallet">👛 Wallet</label></li>
    </ul>
  </div>

  <div class="content" id="details-container">
    <h3>Select a payment mode to proceed.</h3>
  </div>

  <script>
    function showDetails(mode) {
      let html = "";
      if (mode === "card") {
     html = `
  <div style="max-width:350px; width:100%;">
    <h3 style="display:flex; justify-content:space-between; align-items:center;">
      Payment 
      <span>
        <img src="https://img.icons8.com/color/32/visa.png"/>
        <img src="https://img.icons8.com/color/32/mastercard-logo.png"/>
        <img src="https://img.icons8.com/color/32/maestro.png"/>
      </span>
    </h3>
    <form method="post" action="/pay/{{payment_id}}/process" style="display:flex; flex-direction:column;">
      <input type="hidden" name="mode" value="card">
      
      <label style="font-size:14px; margin-top:8px;">Cardholder's name</label>
      <input type="text" name="card_name" placeholder="John Doe" required 
             style="padding:10px; border:1px solid #ccc; border-radius:6px;">
      
      <label style="font-size:14px; margin-top:8px;">Card Number</label>
      <input type="text" name="card_no" maxlength="19" placeholder="0123 4567 8901 2345" required
             style="padding:10px; border:1px solid #ccc; border-radius:6px;">
      
      <div style="display:flex; gap:15px; margin-top:8px;">
        <div style="flex:1;">
          <label style="font-size:14px;">Expiry date</label>
          <input type="text" name="expiry" placeholder="MM/YY" required
                 style="padding:10px; border:1px solid #ccc; border-radius:6px; width:100%;">
        </div>
        <div style="flex:1;">
          <label style="font-size:14px;">CVV</label>
          <input type="password" name="cvv" maxlength="3" placeholder="•••" required
                 style="padding:10px; border:1px solid #ccc; border-radius:6px; width:100%;">
        </div>
      </div>

      <label style="margin-top:10px; font-size:14px;">
        <input type="checkbox" name="save_card"> Save card details to wallet
      </label>

      <div style="display:flex; gap:10px; margin-top:15px;">
        <button type="submit" name="status" value="success"
                style="flex:1; background:#007bff; color:white; border:none; border-radius:6px; padding:10px; cursor:pointer;">
          ✅ Pay
        </button>
        <button type="submit" name="status" value="failed"
                style="flex:1; background:#ccc; border:none; border-radius:6px; padding:10px; cursor:pointer;">
          ❌ Fail
        </button>
      </div>
    </form>
  </div>`;
      } else if (mode === "upi") {
        html = `
          <h3>Scan UPI QR</h3>
          <img src="/upi_qr/{{payment_id}}" width="200" height="200"><br><br>
          <form method="post" action="/pay/{{payment_id}}/process">
            <input type="hidden" name="mode" value="upi">
            <button type="submit" name="status" value="success">✅ Paid</button>
            <button type="submit" name="status" value="failed">❌ Fail</button>
          </form>`;
      } else if (mode === "netbanking") {
        html = `
          <h3>Netbanking</h3>
          <form method="post" action="/pay/{{payment_id}}/process">
            <input type="hidden" name="mode" value="netbanking">
            <select name="bank" required>
              <option value="">Select Bank</option>
              <option>SBI</option>
              <option>HDFC</option>
              <option>ICICI</option>
              <option>Axis</option>
            </select><br>
            <button type="submit" name="status" value="success">✅ Login & Pay</button>
            <button type="submit" name="status" value="failed">❌ Fail</button>
          </form>`;
      } else if (mode === "wallet") {
        html = `
          <h3>Wallet Payment</h3>
          <form method="post" action="/pay/{{payment_id}}/process">
            <input type="hidden" name="mode" value="wallet">
            <input type="text" name="wallet_id" placeholder="Wallet ID" required><br>
            <button type="submit" name="status" value="success">✅ Pay</button>
            <button type="submit" name="status" value="failed">❌ Fail</button>
          </form>`;
      }
      document.getElementById("details-container").innerHTML = html;
    }

    // Session Timer
    const expiry = new Date("{{expiry_iso}}").getTime();
    const timerElement = document.getElementById("timer");
    const countdown = setInterval(() => {
      const now = new Date().getTime();
      const diff = expiry - now;
      if (diff <= 0) {
        clearInterval(countdown);
        timerElement.innerHTML = "⏳ Session expired";
        document.getElementById("details-container").innerHTML = "<h3 style='color:red;'>Session Expired!</h3>";
        return;
      }
      const mins = Math.floor(diff / 60000);
      const secs = Math.floor((diff % 60000) / 1000);
      timerElement.innerHTML = `⏳ Expires in ${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }, 1000);
  </script>
</body>
</html>
"""

@app.route("/create_payment", methods=["POST"])
def create_payment():
    data = request.json
    payment_id = str(uuid.uuid4())
    PAYMENTS[payment_id] = {
        "amount": data.get("amount"),
        "status": "created",
        "callback_url": data.get("callback_url"),
        "mode": None,
        "expiry": datetime.datetime.utcnow() + datetime.timedelta(minutes=SESSION_TIMEOUT)
    }
    return jsonify({
        "payment_id": payment_id,
        "redirect_url": f"http://127.0.0.1:5000/pay/{payment_id}"
    })

@app.route("/upi_qr/<payment_id>")
def upi_qr(payment_id):
    if payment_id not in PAYMENTS:
        return "Invalid Payment ID", 404
    # Generate QR with dummy UPI string
    upi_link = f"upi://pay?pa=test@upi&pn=QuickPay&am={PAYMENTS[payment_id]['amount']}&tn={payment_id}"
    img = qrcode.make(upi_link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/pay/<payment_id>", methods=["GET"])
def pay(payment_id):
    payment = PAYMENTS.get(payment_id)
    if not payment:
        return "Invalid Payment ID", 404
    if datetime.datetime.utcnow() > payment["expiry"]:
        return "<h2 style='color:red;text-align:center;'>Session Expired</h2>"
    return render_template_string(mode_page, payment_id=payment_id, amount=payment["amount"], expiry_iso=payment["expiry"].isoformat()+"Z")

@app.route("/pay/<payment_id>/process", methods=["POST"])
def process_payment(payment_id):
    payment = PAYMENTS.get(payment_id)
    if not payment:
        return "Invalid Payment ID", 404
    if datetime.datetime.utcnow() > payment["expiry"]:
        return "<h2 style='color:red;text-align:center;'>Session Expired</h2>"

    mode = request.form.get("mode")
    status = request.form.get("status")
    payment["mode"] = mode
    payment["status"] = status

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
            requests.post(payment["callback_url"], json=payload, headers={"X-FlyPay-Signature": signature})
        except Exception as e:
            print("Webhook failed:", e)

    threading.Thread(target=send_webhook).start()
    return f"<h2 style='text-align:center;'>QuickPay Payment {status.upper()} via {mode.upper()}</h2>"

if __name__ == "__main__":
    app.run(port=5000, debug=True)
