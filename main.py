from fastapi import FastAPI, Request, Response
import requests
import g4f # আপনার আগের ব্যবহৃত ফ্রি GPT-4 লাইব্রেরি

app = FastAPI()

# আপনার Facebook ডেভেলপার পোর্টাল থেকে এগুলো পেতে হবে
VERIFY_TOKEN = "my_custom_secure_token_123"
PAGE_ACCESS_TOKEN = "EAAIpjqXkeewBSjRQLV7NOh3NwG5deKtelCRrz4iV5sayZBprRh4ZAncddNnSzSNzlzUAIA3KY7NHLcORiRsnmVdQ0wkkybsCD4Q1HA7ZAgUI7268fZAcv9ppIzOpX7aVgZBnG9XGdkIrELoMk56Ow9w6GCoNjxGxRZCiMtMjfLxk56ROEBYyuk1VqmTukGUzZA8MA5qDFk1esZBkcjHMTqvB0VJHs029UCYyB6wkWtbYiOthKxzgeXGgHkguvhRi38EbFv9SVBYMQd3e1pR4vuEm"

# AI থেকে ডায়নামিক রিপ্লাই জেনারেট করার ফাংশন
def get_ai_reply(comment_text):
    try:
        print(f"AI-এর কাছে পাঠানো হচ্ছে: {comment_text}")
        # g4f ব্যবহার করে ফ্রি GPT-4 কল করা
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=[
                {"role": "system", "content": "You are a helpful customer support bot for a Facebook page. Reply clearly and politely in Bengali or English based on the user's language. Keep it short."},
                {"role": "user", "content": comment_text}
            ]
        )
        return response
    except Exception as e:
        print(f"AI Error: {e}")
        return "ধন্যবাদ আপনার মন্তব্যের জন্য! আমরা শীঘ্রই যোগাযোগ করছি।" # AI ফেইল করলে ডিফল্ট রিপ্লাই

# Facebook-এ রিপ্লাই পোস্ট করার ফাংশন
def reply_to_facebook_comment(comment_id, message):
    url = f"https://graph.facebook.com/v18.0/{comment_id}/comments"
    payload = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("রিপ্লাই সফলভাবে পোস্ট হয়েছে!")
    else:
        print(f"Error posting reply: {response.text}")

# ১. Webhook ভেরিফিকেশন (Facebook প্রথমবার কানেক্ট করার সময় এটি চেক করবে)
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("Webhook Verified!")
            return Response(content=challenge, status_code=200)
    return Response(content="Verification failed", status_code=403)

# ২. কমেন্ট রিসিভ এবং রিপ্লাই দেওয়া (কেউ কমেন্ট করলে Facebook এখানে ডেটা পাঠাবে)
@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # চেক করা হচ্ছে এটি কোনো কমেন্ট কি না এবং আমাদের নিজেদের করা রিপ্লাই কি না
                if change.get("field") == "feed" and value.get("item") == "comment" and value.get("verb") == "add":
                    comment_id = value.get("comment_id")
                    message = value.get("message")
                    sender_id = value.get("from", {}).get("id")
                    
                    # পেজ নিজে কমেন্ট করলে যেন লুপ না হয়, তাই সেটি বাদ দেওয়া
                    # (এখানে আপনার পেজের আইডি চেক করা উচিত)
                    
                    print(f"নতুন কমেন্ট এসেছে: {message}")
                    
                    # AI থেকে রিপ্লাই জেনারেট করা
                    ai_reply = get_ai_reply(message)
                    print(f"AI রিপ্লাই দিয়েছে: {ai_reply}")
                    
                    # Facebook-এ রিপ্লাই পাঠানো
                    reply_to_facebook_comment(comment_id, ai_reply)
                    
    return Response(content="EVENT_RECEIVED", status_code=200)
