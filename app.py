from flask import Flask, request
import requests
import yt_dlp
import time

app = Flask(__name__)

PAGE_ACCESS_TOKEN = "EAASKJ7rjAZBUBRCnDeAP8GZC0T0C8yrozZBcAun2cv8buyfMBy7EdNFpzyInRorJQmkq7IKZAwVaCZADbBE3AdUSLAGNZCi1fb4cidZCQkQ0e2wr8MsJtWx4pwUTAZBV6OZCwJNmcu4JtfLZCBnN4uRqIfRBnzLyUWvtoPOGOQeE3sD4XSkIGizvNrFxVQUBnRxK2vRay2ck6nqwZDZD"
VERIFY_TOKEN = "YOUR_VERIFY_TOKEN"

user_results = {}
last_msg_time = {}
known_users = {}

MAX_SIZE_MB = 20

# =========================
# إرسال رسالة
# =========================
def send_message(psid, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

# =========================
# إرسال فيديو
# =========================
def send_video(psid, video_url):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {
            "attachment": {
                "type": "video",
                "payload": {
                    "url": video_url,
                    "is_reusable": True
                }
            }
        }
    }
    requests.post(url, json=payload)

# =========================
# البحث
# =========================
def search_youtube(query):
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        data = ydl.extract_info(f"ytsearch10:{query}", download=False)

    return [
        {"title": v["title"], "url": v["url"]}
        for v in data["entries"]
    ]

# =========================
# جلب الفيديو
# =========================
def get_video_info(url):
    ydl_opts = {
        "quiet": True,
        "format": "best"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    size = info.get("filesize") or info.get("filesize_approx") or 0
    size_mb = size / (1024 * 1024)

    return info["url"], size_mb

# =========================
# Webhook
# =========================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error"

    data = request.get_json()

    for entry in data["entry"]:
        for msg in entry["messaging"]:

            psid = msg["sender"]["id"]
            now = time.time()

            # Anti-spam
            if psid in last_msg_time and now - last_msg_time[psid] < 4:
                send_message(psid, "⛔ صبر شوية")
                continue

            last_msg_time[psid] = now

            # أول مرة
            if psid not in known_users:
                known_users[psid] = True

                send_message(psid,
                    "👋 مرحبا بك\n\n"
                    "🔎 اكتب اسم الفيديو\n"
                    "🎯 اختار رقم من القائمة\n"
                    f"⚖️ الحد: {MAX_SIZE_MB}MB\n\n"
                    "📌 أوامر:\n"
                    "help - شرح\n"
                    "cancel - إلغاء\n"
                )
                continue

            if "message" not in msg:
                continue

            text = msg["message"].get("text", "").lower().strip()

            # =========================
            # أوامر
            # =========================
            if text == "help":
                send_message(psid,
                    "📖 طريقة الاستعمال:\n"
                    "1️⃣ كتب اسم الفيديو\n"
                    "2️⃣ اختار رقم\n\n"
                    "cancel لإلغاء العملية"
                )
                continue

            if text == "cancel":
                user_results.pop(psid, None)
                send_message(psid, "❌ تم الإلغاء")
                continue

            # =========================
            # اختيار رقم
            # =========================
            if text.isdigit():

                if psid not in user_results:
                    send_message(psid, "❌ دير بحث الأول")
                    continue

                choice = int(text)

                if 0 < choice <= len(user_results[psid]):

                    video = user_results[psid][choice - 1]

                    send_message(psid, "⏳ جاري الفحص...")

                    try:
                        direct_url, size_mb = get_video_info(video["url"])

                        if size_mb > MAX_SIZE_MB:
                            send_message(psid, f"❌ الفيديو كبير ({round(size_mb,2)}MB)")
                            continue

                        try:
                            send_video(psid, direct_url)
                        except:
                            send_message(psid, f"🔗 تعذر إرسال الفيديو:\n{video['url']}")

                    except:
                        send_message(psid, "❌ خطأ في الفيديو")

                else:
                    send_message(psid, "❌ رقم غير صحيح")

                continue

            # =========================
            # بحث
            # =========================
            results = search_youtube(text)[:7]
            user_results[psid] = results

            msg_text = "🎬 قائمة الفيديوهات\n"
            msg_text += "=======================\n"

            for i, v in enumerate(results, 1):
                msg_text += f"{i} == {v['title'][:40]}\n"

            msg_text += "=======================\n"
            msg_text += "👉 اختار رقم الفيديو\n"
            msg_text += "❌ cancel للإلغاء"

            send_message(psid, msg_text)

    return "ok"


if __name__ == "__main__":
    app.run(port=5000, debug=True)
