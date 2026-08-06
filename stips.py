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


def pretvori_u_broj(vrednost):
    if vrednost is None:
        return None

    return float(vrednost.replace(".", "").replace(",", "."))


def datum_clanka(tekst):
    poklapanje = re.search(
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
        tekst
    )

    if not poklapanje:
        return None

    dan, mesec, godina = map(int, poklapanje.groups())

    try:
        return datetime(godina, mesec, dan)
    except ValueError:
        return None


def pronadji_najnoviji_izvestaj():
    kandidati = []
    vidjeni = set()

    # Pregledamo nekoliko prvih strana arhive
    for broj_strane in range(3):
        url = ARHIVA_URL if broj_strane == 0 else f"{ARHIVA_URL}?page={broj_strane}"

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            naslov = normalizuj_tekst(link.get_text(" ", strip=True))
            naslov_mali = naslov.lower()

            if "promet robe na produktnoj berzi" not in naslov_mali:
                continue

            puni_link = urljoin(BASE_URL, link["href"])

            if puni_link in vidjeni:
                continue

            vidjeni.add(puni_link)
            kandidati.append(puni_link)

    if not kandidati:
        raise RuntimeError(
            "Nije pronađen nijedan STIPS izveštaj Produktne berze."
        )

    # Otvaramo pronađene članke i biramo onaj sa najnovijim datumom objave
    provereni = []

    for link in kandidati[:20]:
        try:
            response = requests.get(
                link,
                headers=HEADERS,
                timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            tekst = normalizuj_tekst(soup.get_text(" ", strip=True))
            datum = datum_clanka(tekst)

            if datum:
                provereni.append((datum, link, tekst))

        except requests.RequestException as greska:
            print("Preskačem link zbog greške:", link, greska)

    if not provereni:
        raise RuntimeError(
            "Pronađeni su linkovi, ali nije moguće utvrditi datum izveštaja."
        )

    provereni.sort(key=lambda stavka: stavka[0], reverse=True)

    datum, link, tekst = provereni[0]

    print("NAJNOVIJI IZVEŠTAJ:")
    print(link)
    print("Datum objave:", datum.strftime("%d.%m.%Y"))

    return link, tekst


def izdvoji_deo(tekst, pocetak, sledece_reci):
    tekst_mali = tekst.lower()
    pozicija = tekst_mali.find(pocetak.lower())

    if pozicija == -1:
        return ""

    kraj = len(tekst)

    for rec in sledece_reci:
        sledeca_pozicija = tekst_mali.find(
            rec.lower(),
            pozicija + len(pocetak)
        )

        if sledeca_pozicija != -1:
            kraj = min(kraj, sledeca_pozicija)

    return tekst[pozicija:kraj]


def pronadji_cenu(deo, obrasci):
    for obrazac in obrasci:
        rezultat = re.search(
            obrazac,
            deo,
            flags=re.IGNORECASE
        )

        if rezultat:
            return pretvori_u_broj(rezultat.group(1))

    return None


def uzmi_cene():
    link, tekst = pronadji_najnoviji_izvestaj()

    deo_kukuruz = izdvoji_deo(
        tekst,
        "kukuruz",
        ["pšenic", "psenic", "soj", "ječam", "jecam"]
    )

    deo_psenica = izdvoji_deo(
        tekst,
        "pšenic",
        ["soj", "kukuruz", "ječam", "jecam"]
    )

    deo_soja = izdvoji_deo(
        tekst,
        "soj",
        ["ječam", "jecam", "uljana repica", "suncokret"]
    )

    kukuruz = pronadji_cenu(
        deo_kukuruz,
        [
            r"ponder(?:isana)? cena iznosila je\s*(\d+[.,]\d+)",
            r"prosečna cena iznosila je\s*(\d+[.,]\d+)",
            r"prosecna cena iznosila je\s*(\d+[.,]\d+)"
        ]
    )

    psenica = pronadji_cenu(
        deo_psenica,
        [
            r"prosečna cena iznosila je\s*(\d+[.,]\d+)",
            r"prosecna cena iznosila je\s*(\d+[.,]\d+)",
            r"ponder(?:isana)? cena iznosila je\s*(\d+[.,]\d+)"
        ]
    )

    soja = pronadji_cenu(
        deo_soja,
        [
            r"zaključeni su po ceni od\s*(\d+[.,]\d+)",
            r"zakljuceni su po ceni od\s*(\d+[.,]\d+)",
            r"ponder(?:isana)? cena iznosila je\s*(\d+[.,]\d+)",
            r"prosečna cena iznosila je\s*(\d+[.,]\d+)",
            r"prosecna cena iznosila je\s*(\d+[.,]\d+)"
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

    if all(vrednost is None for vrednost in cene.values()):
        raise RuntimeError(
            "Najnoviji izveštaj je pronađen, ali nijedna cena nije izvučena."
        )

    return cene
