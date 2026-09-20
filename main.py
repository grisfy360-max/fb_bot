from fastapi import FastAPI, Request, Response
import requests
import json

app = FastAPI()

# আপনার Facebook ডেভেলপার পোর্টাল থেকে এগুলো পেতে হবে
VERIFY_TOKEN = "my_custom_secure_token_123"
PAGE_ACCESS_TOKEN = "EAAIpjqXkeewBSl87a9Pxa7l3rZCQ8fB9LTpiXLajmkRD49O0ND80YG8j2ZBDXBonMgpvvBl9afoST67NHVEMVn2m15rTZCUhu9WOnqFxZChVIGZCVUZCJaofSg5N7D0uSB04NiUsCVTvErw52DGYirXM4BAfE4jZARhHZBCMXqrQUdrvtXb9ZBgM22q7oybHRu8QHZANZAa2QrAzM51cCDWPG6torfZC26tEZCzn6Lep4QcEZD"
GEMINI_API_KEY = "AQ.Ab8RN6KYfgon" + "xC7ggBpEfozn_f0MFhFNJqieJp6Shs0S23n5-g"

# AI থেকে ডায়নামিক রিপ্লাই জেনারেট করার ফাংশন
def get_ai_reply(comment_text):
    system_prompt = "You are a friendly human Facebook admin for 'HumanRights' in Bangladesh. CRITICAL RULES: 1. You MUST reply ONLY in pure Bengali script (বাংলা অক্ষরে). 2. NEVER use Chinese, English, or any other language. 3. If the user writes in Banglish, reply in pure Bengali script. 4. Keep it very short (1-2 sentences max). Understand their question and answer directly."
    
    # আমরা লেটেস্ট ভার্সন থেকে শুরু করে নিচের দিকে নামব (Fallback)
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite"
    ]
    
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": comment_text}]}]
    }

    for model_name in models_to_try:
        try:
            print(f"[{model_name}] দিয়ে ট্রাই করা হচ্ছে...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            
            res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
            res.raise_for_status() # 429 (Rate Limit) বা অন্য এরর হলে Exception থ্রো করবে
            
            reply_text = res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if reply_text:
                return reply_text.strip()
                
        except Exception as e:
            print(f"[{model_name}] ফেইল করেছে ({e}) - পরবর্তী মডেলে শিফট করা হচ্ছে...")
            continue # বর্তমান মডেল ফেইল করলে লুপের পরবর্তী মডেলে চলে যাবে

    # যদি উপরের সবগুলো মডেল ফেইল করে, তখন ডিফল্ট মেসেজ দেবে
    print("সবগুলো Gemini মডেল ফেইল করেছে!")
    return "ধন্যবাদ আপনার মন্তব্যের জন্য! আমরা শীঘ্রই যোগাযোগ করছি।"

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
    print("Incoming Webhook Data:", data)
    
    if data.get("object") == "page":
        PAGE_ID = "1074840362368242"
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # চেক করা হচ্ছে এটি কোনো কমেন্ট কি না এবং আমাদের নিজেদের করা রিপ্লাই কি না
                if change.get("field") == "feed" and value.get("item") == "comment" and value.get("verb") == "add":
                    comment_id = value.get("comment_id")
                    message = value.get("message")
                    sender_id = value.get("from", {}).get("id")
                    
                    # পেজ নিজে কমেন্ট করলে যেন লুপ না হয়, তাই সেটি বাদ দেওয়া
                    if sender_id == PAGE_ID:
                        print("নিজেদের কমেন্ট (বটের রিপ্লাই), তাই স্কিপ করা হলো।")
                        continue
                    
                    print(f"নতুন কমেন্ট এসেছে: {message}")
                    
                    # AI থেকে রিপ্লাই জেনারেট করা
                    ai_reply = get_ai_reply(message)
                    print(f"AI রিপ্লাই দিয়েছে: {ai_reply}")
                    
                    # Facebook-এ রিপ্লাই পাঠানো
                    reply_to_facebook_comment(comment_id, ai_reply)
                    
    return Response(content="EVENT_RECEIVED", status_code=200)
