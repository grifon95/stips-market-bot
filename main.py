import os
import requests
from datetime import datetime

from stips import uzmi_cene
from istorija import sacuvaj_cene
from analiza import napravi_analizu


print("🚀 STIPS BOT START")


datum = datetime.now().strftime("%d.%m.%Y")


# uzimamo cene sa STIPS-a
cene = uzmi_cene()

print("IZVUČENO:")
print(cene)


# čuvamo istoriju
istorija = sacuvaj_cene(cene)


print("\nISTORIJA:")
print(istorija)


# pravimo analizu
analiza = napravi_analizu()


print("\nANALIZA:")
print(analiza)



# ako nema dovoljno podataka, ipak šaljemo cenu
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



# TELEGRAM

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


print("\nTelegram:")
print(response.text)
