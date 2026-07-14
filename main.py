import os
import requests
from datetime import datetime

from stips import uzmi_cene
from istorija import sacuvaj_cene
from analiza import napravi_analizu
from grafikon import napravi_grafikon


print("🚀 STIPS BOT START")


datum = datetime.now().strftime("%d.%m.%Y")


# =========================
# UZIMANJE CENA
# =========================

cene = uzmi_cene()

print("IZVUČENO:")
print(cene)



# =========================
# ČUVANJE ISTORIJE
# =========================

istorija = sacuvaj_cene(cene)

print("\nISTORIJA:")
print(istorija)



# =========================
# ANALIZA
# =========================

analiza = napravi_analizu()

print("\nANALIZA:")
print(analiza)



# =========================
# GRAFIKON
# =========================

grafikon = napravi_grafikon()

print("\nGrafikon napravljen:")
print(grafikon)



# =========================
# TELEGRAM PORUKA
# =========================


if "Nema dovoljno podataka" in analiza:

    poruka = f"""
📊 STIPS MARKET ALERT

Datum: {datum}

🌾 Pšenica:
{cene['psenica']} din/kg

🌽 Kukuruz:
{cene['kukuruz']} din/kg

🫘 Soja:
{cene['soja']} din/kg


⚠️ Još nema dovoljno istorije za trend analizu.
"""

else:

    poruka = f"""
📊 STIPS MARKET ALERT

Datum: {datum}


{analiza}
"""



print("\nPORUKA:")
print(poruka)



# =========================
# SLANJE TEKSTA
# =========================

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


print("\nTelegram tekst:")
print(response.text)



# =========================
# SLANJE GRAFIKONA
# =========================

url_slika = f"https://api.telegram.org/bot{token}/sendPhoto"


with open("grafikon_cena.png", "rb") as slika:

    response_slika = requests.post(
        url_slika,
        data={
            "chat_id": chat_id,
            "caption": "📈 STIPS grafikon cena"
        },
        files={
            "photo": slika
        }
    )


print("\nTelegram slika:")
print(response_slika.text)
