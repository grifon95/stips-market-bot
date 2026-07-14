import os
from datetime import datetime
import requests


print("🚀 STIPS BOT START")


datum = datetime.now().strftime("%d.%m.%Y")


poruka = f"""
📊 STIPS MARKET ALERT

Datum: {datum}

✅ GitHub Action radi!
"""


token = os.environ["BOT_TOKEN"]
chat_id = os.environ["CHAT_ID"]


url = f"https://api.telegram.org/bot{token}/sendMessage"


response = requests.post(
    url,
    data={
        "chat_id": chat_id,
        "text": poruka
    }
)


print(response.text)
