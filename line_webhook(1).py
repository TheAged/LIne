from fastapi import FastAPI, Request
from pydantic import BaseModel
from pymongo import MongoClient
import requests
import uvicorn

# === 設定 ===
LINE_TOKEN = "QGOaQJM4AdaK450cGKj9XbeBrfVj36IQyPMEjH59q1hGYggKnBXkAUJeEfwmbAdVW59ALYEMAaJXgsgOBAJHkSPxymsHtgdwoVOwVDzuYjTkGA29D+/jeZOKp4/GenDu4jPr3WIwpToZ/dsn0EKbaQdB04t89/1O/w1cDnyilFU="
MONGO_URL = "mongodb://b310:pekopeko878@localhost:27017/?authSource=admin"
DB_NAME = "userdb"
COLLECTION = "line"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

# === 初始化 ===
app = FastAPI()
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
line = db[COLLECTION]

# === Webhook 接收 ===
@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    print("📩 收到 LINE Webhook:", body)

    events = body.get("events", [])
    if events:
        user_id = events[0]["source"].get("userId")
        message = events[0]["message"].get("text")
        print(f"✅ 抓到 userId: {user_id}, 訊息: {message}")

        if user_id:
            line.update_one(
                {"lineId": user_id},
                {"$set": {"lineId": user_id}},
                upsert=True
            )
            print("💾 已存進 MongoDB")

    return {"status": "ok"}

# === 測試 API ===
@app.get("/test")
async def test():
    return {"msg": "🚀 LINE Webhook server is running!"}

# === 單一用戶推播 ===
class NotifyRequest(BaseModel):
    userId: str
    message: str

@app.post("/notify")
async def notify(data: NotifyRequest):
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {
        "to": data.userId,
        "messages": [{"type": "text", "text": data.message}]
    }
    r = requests.post(LINE_PUSH_URL, headers=headers, json=payload)
    try:
        resp = r.json()
    except Exception:
        resp = r.text
    return {"status": r.status_code, "response": resp}

# === 全體推播 ===
class NotifyAllRequest(BaseModel):
    message: str

@app.post("/notifyAll")
async def notify_all(data: NotifyAllRequest):
    users = line.find({}, {"lineId": 1})
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    for u in users:
        if not u.get("lineId"):
            continue
        payload = {
            "to": u["lineId"],
            "messages": [{"type": "text", "text": data.message}]
        }
        requests.post(LINE_PUSH_URL, headers=headers, json=payload)
        print(f"📤 已推播給 {u['lineId']}")
    return {"status": "✅ 已推播所有用戶", "message": data.message}

# === 查詢所有用戶 userId（for 自動推播用） ===
@app.get("/userIds")
async def user_ids():
    users = line.find({}, {"lineId": 1, "_id": 0})
    return {"userIds": [u["lineId"] for u in users if "lineId" in u]}

# === 啟動 ===
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)
