from fastapi import FastAPI, Request, Response
import requests
import json

app = FastAPI()

# আপনার Facebook ডেভেলপার পোর্টাল থেকে এগুলো পেতে হবে
VERIFY_TOKEN = "my_custom_secure_token_123"
PAGE_ACCESS_TOKEN = "EAAIpjqXkeewBSl87a9Pxa7l3rZCQ8fB9LTpiXLajmkRD49O0ND80YG8j2ZBDXBonMgpvvBl9afoST67NHVEMVn2m15rTZCUhu9WOnqFxZChVIGZCVUZCJaofSg5N7D0uSB04NiUsCVTvErw52DGYirXM4BAfE4jZARhHZBCMXqrQUdrvtXb9ZBgM22q7oybHRu8QHZANZAa2QrAzM51cCDWPG6torfZC26tEZCzn6Lep4QcEZD"
GEMINI_API_KEY = "AQ.Ab8RN6KYfgon" + "xC7ggBpEfozn_f0MFhFNJqieJp6Shs0S23n5-g"
OPENROUTER_API_KEY = "sk-or-v1-" + "c815c67e095bb5b485c369cdf60df3ef84953d504501778d21268cb8429321d0"

# AI থেকে ডায়নামিক রিপ্লাই জেনারেট করার ফাংশন
def get_ai_reply(comment_text):
    system_prompt = "You are a friendly human Facebook admin for 'HumanRights' in Bangladesh. CRITICAL RULES: 1. You MUST reply ONLY in pure Bengali script (বাংলা অক্ষরে). 2. NEVER use Chinese, English, or any other language. 3. If the user writes in Banglish, reply in pure Bengali script. 4. Keep it very short (1-2 sentences max). Understand their question and answer directly."
    
    # প্রথমে Gemini দিয়ে ট্রাই করবে (Primary Model)
    try:
        print(f"Gemini-তে পাঠানো হচ্ছে: {comment_text}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": comment_text}]}]
        }
        res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
        res.raise_for_status() # HTTP Error (যেমন 429 Rate Limit) হলে এক্সেপশন থ্রো করবে
        
        reply_text = res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if reply_text: return reply_text.strip()
    except Exception as e:
        print(f"Gemini Error/Rate Limit ({e}) - Shifting to OpenRouter dynamically...")

    # জেমিনি ফেইল করলে OpenRouter-এ শিফট করবে (Fallback Model)
    try:
        res2 = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "openrouter/free", 
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": comment_text}
                ]
            }
        )
        res2.raise_for_status()
        reply_text2 = res2.json()["choices"][0]["message"]["content"]
        if reply_text2: return reply_text2.strip()
    except Exception as e2:
        print(f"OpenRouter Error ({e2}) - All AI failed.")

    # যদি দুটোই ফেইল করে, তখন ডিফল্ট মেসেজ দেবে
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
