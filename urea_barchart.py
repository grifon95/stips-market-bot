import re
import requests


URL = "https://www.barchart.com/futures/quotes/JCQ26/comparison"

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


    # Tražimo delove oko ključnih polja
    for rec in [
        "Latest",
        "Previous Close",
        "% Change",
        "JCQ26"
    ]:

        pozicija = html.find(rec)

        print("\n================")
        print("TRAZIM:", rec)
        print("================")

        if pozicija == -1:
            print("NIJE PRONADJENO")
        else:
            print(
                html[
                    max(0, pozicija - 500):
                    pozicija + 1500
                ]
            )


    # Probni regex za cenu
    obrasci = [
        r"Latest.{0,500}?(\d{3}(?:\.\d+)?)",
        r"Previous Close.{0,500}?(\d{3}(?:\.\d+)?)"
    ]


    for obrazac in obrasci:

        rezultat = re.search(
            obrazac,
            html,
            flags=re.IGNORECASE | re.DOTALL
        )

        if rezultat:

            print(
                "\nPRONADJEN BROJ:",
                rezultat.group(1)
            )


    print("\n✅ COMPARISON STRANICA PROCITANA")
