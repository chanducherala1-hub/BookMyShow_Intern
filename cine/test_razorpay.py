import razorpay

KEY_ID = "YOUR_NEW_TEST_KEY_ID"
KEY_SECRET = "YOUR_NEW_TEST_SECRET"

client = razorpay.Client(
    auth=(KEY_ID, KEY_SECRET)
)

try:
    order = client.order.create({
        "amount": 10000,
        "currency": "INR",
        "receipt": "test_receipt_001"
    })

    print("SUCCESS")
    print(order)

except Exception as e:
    print("ERROR:", e)