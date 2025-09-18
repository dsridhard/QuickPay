from flask import Flask,request,jsonify,redirect,render_template_string
import uuid ,hmac ,hashlib,requests,json,threading


app =Flask(__name__)

#In-memory store for payments
payments ={}

# Shared secret for webhook signing 
#  (merchant must verify this)

WEBHOOK_SECRET = "quickpay_secret"


#1 Create a payment

@app.route("/create_payment",methods=["POST"])
def create_payment():
    data =request.json
    payment_id = str(uuid.uuid4())

    payments[payment_id] ={
        "amount":data.get("amount"),
        "currency":data.get("currency","INR"),
        "status":"created",
        "return_url":data.get("return_url"),
        "webhook_url":data.get("webhook_url")
    }
    pay_url = f"http://localhost:5000/pay/{payment_id}"
    return jsonify({"payment_id":payment_id,"pay_url":pay_url})

#2 Payment Page

@app.route("/pay/<payment_id>",
           methods=["GET"])
def pay_page(payment_id):
    if payment_id not in payments:
        return "Invalid payment_id",404
    
    html = f"""
           <h1>Payment Gateway</h1>
           <p>Amount :{payments[payment_id]}</p>
           ['amount']{payments[payment_id]['currency']}</p>
           <form action="/simulate/{payment_id}" method="post">
           <button name="status" value="success">Simulate Success ✅ </button>
           <button name="status" value="faliure">Simulate Failure ❌ </button>
           <button name="status" value="pending">Simulate Pending ❗ </button>
           </form>
             
             """
    return render_template_string(html)

# 3 Simulate Payment Outcome
@app.route("/simulate/payment_id",
           methods=["POST"])
def simulate(payment_id):
    if payment_id not in payments:
        return "Invalid payment_id",404
    status = request.form.get("status")
    payments[payment_id]["status"]= status
    
    #Fire  webhook in a background thread (non-blocking)
    webhook_url = payments[payment_id]["webhook_url"]
    if webhook_url:threading.Thread(target=send_webhook,args=(payment_id,status,webhook_url)).start()

    return_url =payments[payment_id]["return_url"]
    if return_url:
        return redirect(f"{return_url}?payment_id={payment_id}&status={status}")
    return f"Payment {payment_id} set to {status}"



# 4 check status API 
@app.route("/status/<payment_id>",
           methods=["POST"])
def status(payment_id):
    if payment_id not in payments:
        return jsonify({"error":"Invalid payment_id"}),404
    
    return jsonify({"payment_id":payment_id,"status":payments[payment_id]["status"]})



# Utility : Send Webhook with HMAC

def send_webhook(payment_id,status,url):
    payload ={
        "payment_id":payment_id,
        "status":status,
        "amount":payments[payment_id]["amount"],
        "currency":payments[payment_id]["currency"]
    }
    body =json.dumps(payload)
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body.encode(),hashlib.sha256
    ).hexdigest()

    headers={
        "content-Type":"application/json",
        "X-Dummy-Signature":signature
    }
    try:
        requests.post(url,data=body,
                      headers=headers,timeout=5)
    except Exception as e :
        print(f"⚠️ webhook delivery failed:{e}")

if __name__ == '__main__':
    app.run(port=5000,debug=True)     