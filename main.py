import os
import sys
import requests
from datetime import datetime

from stips import uzmi_cene
from istorija import sacuvaj_cene
from analiza import napravi_analizu
from grafikon import napravi_grafikon


print("🚀 STIPS BOT START")


datum = datetime.now().strftime("%d.%m.%Y")

token = os.environ["BOT_TOKEN"]
chat_id = os.environ["CHAT_ID"]


def posalji_telegram_poruku(tekst):
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": tekst
        },
        timeout=30
    )

    print("\nTelegram tekst status:", response.status_code)
    print(response.text)

    response.raise_for_status()


def posalji_grafikon(putanja):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    with open(putanja, "rb") as slika:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "caption": "📈 STIPS grafikon cena"
            },
            files={
                "photo": slika
            },
            timeout=60
        )

    print("\nTelegram slika status:", response.status_code)
    print(response.text)

    response.raise_for_status()


try:
    # =========================
    # UZIMANJE CENA
    # =========================

    cene = uzmi_cene()

    print("\nIZVUČENO:")
    print(cene)


    # Provera da li neka cena nedostaje
    nedostajuce_cene = [
        proizvod
        for proizvod, cena in cene.items()
        if cena is None
    ]

    if nedostajuce_cene:
        raise RuntimeError(
            "Nisu pronađene cene za: "
            + ", ".join(nedostajuce_cene)
        )


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

    print("\nGRAFIKON NAPRAVLJEN:")
    print(grafikon)


    # =========================
    # PRAVLJENJE PORUKE
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
    # SLANJE NA TELEGRAM
    # =========================

    posalji_telegram_poruku(poruka)
    posalji_grafikon(grafikon)

    print("\n✅ STIPS BOT JE USPEŠNO ZAVRŠIO RAD")


except Exception as greska:

    print("\n❌ GREŠKA:")
    print(str(greska))


    upozorenje = f"""
⚠️ STIPS BOT GREŠKA

Datum: {datum}

Bot nije uspeo da preuzme ili obradi najnovije STIPS cene.

Mogući razlozi:
• STIPS je promenio format izveštaja
• STIPS sajt trenutno nije dostupan
• jedna ili više cena nisu pronađene
• došlo je do greške u scraperu

Detalj greške:
{str(greska)}

Proveri GitHub Actions log.
"""


    try:
        posalji_telegram_poruku(upozorenje)

    except Exception as telegram_greska:
        print("\nNije moguće poslati Telegram upozorenje:")
        print(str(telegram_greska))


    sys.exit(1)
