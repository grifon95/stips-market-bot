import re
import requests


URL = "https://www.barchart.com/futures/quotes/JCQ26/overview"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126 Safari/537.36"
    )
}


def uzmi_barchart_ureu():

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    print("STATUS:", response.status_code)
    print("DUZINA:", len(response.text))

    response.raise_for_status()

    html = response.text


    # Probamo nekoliko obrazaca koji se pojavljuju
    # u Barchart HTML/JSON podacima

    obrasci = [
        r'"lastPrice"\s*:\s*"?(\\d+(?:\\.\\d+)?)"?',
        r'"last"\s*:\s*"?(\\d+(?:\\.\\d+)?)"?',
        r'"price"\s*:\s*"?(\\d+(?:\\.\\d+)?)"?',
        r'data-ng-value="lastPrice"[^>]*>\\s*(\\d+(?:\\.\\d+)?)',
    ]


    cena = None

    for obrazac in obrasci:

        rezultat = re.search(
            obrazac,
            html,
            flags=re.IGNORECASE
        )

        if rezultat:

            kandidat = float(
                rezultat.group(1)
            )

            # UREA trenutno treba da bude u realnom
            # tržišnom opsegu, ne npr. 1.2 ili 50000
            if 100 <= kandidat <= 1000:

                cena = kandidat

                print(
                    "PRONAĐENA CENA:",
                    cena
                )

                break


    if cena is None:

        print(
            "\n⚠️ Cena nije pronađena standardnim obrascima."
        )

        # Debug: tražimo delove gde se pojavljuje JCQ26
        pozicija = html.find("JCQ26")

        if pozicija != -1:

            print(
                "\nDEO HTML-A OKO JCQ26:"
            )

            print(
                html[
                    max(0, pozicija - 1000):
                    pozicija + 3000
                ]
            )

        raise RuntimeError(
            "Barchart stranica radi, ali cena JCQ26 nije pronađena."
        )


    podaci = {
        "simbol": "JCQ26",
        "naziv": "Urea Granular FOB US Gulf Aug 2026",
        "cena_usd_t": cena,
        "izvor": URL
    }


    print("\nCBOT UREA:")
    print(podaci)


    return podaci
