import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.stips.minpolj.gov.rs"
ARHIVA_URL = f"{BASE_URL}/srl/node"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126 Safari/537.36"
    )
}


def normalizuj_tekst(tekst):
    return re.sub(r"\s+", " ", tekst).strip()


def broj(vrednost):
    if vrednost is None:
        return None

    return float(vrednost.replace(",", "."))


def pronadji_datum(tekst):
    rezultat = re.search(
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
        tekst
    )

    if not rezultat:
        return None

    dan, mesec, godina = map(int, rezultat.groups())

    try:
        return datetime(godina, mesec, dan)
    except ValueError:
        return None


def pronadji_najnoviji_izvestaj():
    kandidati = []
    vidjeni = set()

    # Pregledamo prve tri strane STIPS arhive
    for stranica in range(3):

        if stranica == 0:
            url = ARHIVA_URL
        else:
            url = f"{ARHIVA_URL}?page={stranica}"

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):

            naslov = normalizuj_tekst(
                link.get_text(" ", strip=True)
            )

            if "promet robe na produktnoj berzi" not in naslov.lower():
                continue

            puni_link = urljoin(
                BASE_URL,
                link["href"]
            )

            if puni_link not in vidjeni:
                vidjeni.add(puni_link)
                kandidati.append(puni_link)

    if not kandidati:
        raise RuntimeError(
            "Nije pronađen nijedan STIPS izveštaj."
        )

    provereni = []

    for link in kandidati[:20]:

        try:
            response = requests.get(
                link,
                headers=HEADERS,
                timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            tekst = normalizuj_tekst(
                soup.get_text(" ", strip=True)
            )

            datum = pronadji_datum(tekst)

            if datum:
                provereni.append(
                    (datum, link, tekst)
                )

        except requests.RequestException as greska:
            print(
                "Preskačem link:",
                link,
                greska
            )

    if not provereni:
        raise RuntimeError(
            "Nije moguće utvrditi datum najnovijeg izveštaja."
        )

    provereni.sort(
        key=lambda x: x[0],
        reverse=True
    )

    datum, link, tekst = provereni[0]

    print("NAJNOVIJI IZVEŠTAJ:")
    print(link)
    print(
        "Datum objave:",
        datum.strftime("%d.%m.%Y")
    )

    return link, tekst


def izvuci_prvi_broj(tekst, obrasci):

    for obrazac in obrasci:

        rezultat = re.search(
            obrazac,
            tekst,
            flags=re.IGNORECASE
        )

        if rezultat:
            return broj(rezultat.group(1))

    return None


def uzmi_cene():

    link, tekst = pronadji_najnoviji_izvestaj()

    # KUKURUZ
    kukuruz = izvuci_prvi_broj(
        tekst,
        [
            (
                r"ugovor zaključen je za kukuruz.*?"
                r"po ceni od\s*(\d+,\d+)\s*din/kg"
            ),
            (
                r"kukuruz.*?"
                r"ponder(?:isana)? cena.*?"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"kukuruz.*?"
                r"prosečna cena.*?"
                r"(\d+,\d+)\s*din/kg"
            )
        ]
    )

    # PŠENICA
    psenica = izvuci_prvi_broj(
        tekst,
        [
            (
                r"prosečna cena hlebnog zrna "
                r"iznosila je\s*(\d+,\d+)"
            ),
            (
                r"prosečna cena pšenice "
                r"iznosila je\s*(\d+,\d+)"
            ),
            (
                r"pšenic.*?"
                r"prosečna cena.*?"
                r"(\d+,\d+)\s*din/kg"
            )
        ]
    )

    # SOJA
    soja = izvuci_prvi_broj(
        tekst,
        [
            (
                r"sojinog zrna.*?"
                r"jedinstvenom cenovnom nivou od "
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"sojin.*?"
                r"trgovalo se.*?"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"sojino zrno.*?"
                r"po ceni od\s*(\d+,\d+)"
            )
        ]
    )

    cene = {
        "psenica": psenica,
        "kukuruz": kukuruz,
        "soja": soja
    }

    print("IZVUČENO:")
    print(cene)

    print("IZVOR:")
    print(link)

    if all(
        vrednost is None
        for vrednost in cene.values()
    ):
        raise RuntimeError(
            "Izveštaj je pronađen, ali cene nisu izvučene."
        )

    return cene
