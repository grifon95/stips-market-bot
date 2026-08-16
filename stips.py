import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://nscomex.com"
ARHIVA_URL = (
    "https://nscomex.com/"
    "podaci-iz-trgovanja/nedeljni-izvestaj/"
)

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

    return float(
        vrednost
        .replace(".", "")
        .replace(",", ".")
    )


# =====================================
# PRONALAZAK IZVEŠTAJA
# =====================================

def pronadji_izvestaje():

    linkovi = []
    vidjeni = set()

    # Čitamo nekoliko strana unazad.
    # Dovoljno da pronađemo poslednju trgovanu
    # cenu ako neke robe nema u najnovijoj nedelji.
    for stranica in range(1, 6):

        if stranica == 1:
            url = ARHIVA_URL
        else:
            url = f"{ARHIVA_URL}page/{stranica}/"

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for link_element in soup.find_all(
            "a",
            href=True
        ):

            href = urljoin(
                BASE_URL,
                link_element["href"]
            )

            # Primer:
            # /nedeljni-izvestaj/82-10-08-14-08-2026/
            if "/nedeljni-izvestaj/" not in href:
                continue

            if href.rstrip("/") == ARHIVA_URL.rstrip("/"):
                continue

            if href in vidjeni:
                continue

            # Link mora da sadrži broj izveštaja
            if not re.search(
                r"/nedeljni-izvestaj/\d+",
                href
            ):
                continue

            vidjeni.add(href)
            linkovi.append(href)

    if not linkovi:
        raise RuntimeError(
            "Nisu pronađeni izveštaji Produktne berze."
        )

    izvestaji = []

    for link in linkovi:

        try:
            response = requests.get(
                link,
                headers=HEADERS,
                timeout=30
            )

            response.raise_for_status()

        except requests.RequestException as greska:

            print(
                "Preskačem izveštaj:",
                link,
                greska
            )

            continue

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        tekst = normalizuj_tekst(
            soup.get_text(
                " ",
                strip=True
            )
        )

        h1 = soup.find("h1")

        if h1:
            naslov = normalizuj_tekst(
                h1.get_text(
                    " ",
                    strip=True
                )
            )
        else:
            naslov = ""

        # Primer:
        # #82 (10.08-14.08.2026.)
        rezultat = re.search(
            r"#(\d+)\s*"
            r"\((\d{2})\.(\d{2})"
            r"-(\d{2})\.(\d{2})\.(\d{4})",
            naslov
        )

        if not rezultat:
            continue

        broj_izvestaja = int(
            rezultat.group(1)
        )

        pocetak_dan = rezultat.group(2)
        pocetak_mesec = rezultat.group(3)

        kraj_dan = rezultat.group(4)
        kraj_mesec = rezultat.group(5)
        godina = rezultat.group(6)

        period = (
            f"{pocetak_dan}.{pocetak_mesec}."
            f"-{kraj_dan}.{kraj_mesec}.{godina}."
        )

        datum_kraja = datetime(
            int(godina),
            int(kraj_mesec),
            int(kraj_dan)
        )

        izvestaji.append({
            "broj": broj_izvestaja,
            "period": period,
            "datum": datum_kraja,
            "naslov": naslov,
            "link": link,
            "tekst": tekst
        })

    if not izvestaji:
        raise RuntimeError(
            "Izveštaji su pronađeni, ali nisu obrađeni."
        )

    izvestaji.sort(
        key=lambda x: (
            x["datum"],
            x["broj"]
        ),
        reverse=True
    )

    return izvestaji


# =====================================
# REGEX POMOĆNA FUNKCIJA
# =====================================

def izvuci_prvi_broj(tekst, obrasci):

    for obrazac in obrasci:

        rezultat = re.search(
            obrazac,
            tekst,
            flags=(
                re.IGNORECASE |
                re.DOTALL
            )
        )

        if rezultat:
            return broj(
                rezultat.group(1)
            )

    return None


# =====================================
# KUKURUZ
# =====================================

def izvuci_kukuruz(tekst):

    obrasci = [

        # #82:
        # Prosečna cena iznosila je 20,40 din/kg
        (
            r"tržište kukuruza"
            r".{0,1500}?"
            r"prosečna cena iznosila je\s*"
            r"(\d+,\d+)\s*din/kg"
        ),

        # #81:
        # ...20,30 din/kg ... što ujedno predstavlja
        # i ponder cenu
        (
            r"kukuruz"
            r".{0,1500}?"
            r"(\d+,\d+)\s*din/kg"
            r".{0,200}?"
            r"(?:ponder cena|ponder cenu)"
        ),

        (
            r"kukuruz"
            r".{0,1500}?"
            r"ponder(?:isana)? cena"
            r".{0,100}?"
            r"(\d+,\d+)"
        )
    ]

    return izvuci_prvi_broj(
        tekst,
        obrasci
    )


# =====================================
# PŠENICA
# =====================================

def izvuci_psenicu(tekst):

    obrasci = [

        # #82:
        # Pšenicom se trgovalo po ceni od 19,80...
        # što ujedno predstavlja i ponder cenu.
        (
            r"pšenic"
            r".{0,1200}?"
            r"trgovalo po ceni od\s*"
            r"(\d+,\d+)\s*din/kg"
            r".{0,300}?"
            r"ponder"
        ),

        (
            r"pšenic"
            r".{0,1200}?"
            r"ponder(?:isana)? cena"
            r".{0,100}?"
            r"(\d+,\d+)"
        ),

        (
            r"pšenic"
            r".{0,1200}?"
            r"prosečna cena"
            r".{0,100}?"
            r"(\d+,\d+)"
        )
    ]

    return izvuci_prvi_broj(
        tekst,
        obrasci
    )


# =====================================
# SOJA
# =====================================

def izvuci_soju(tekst):

    # Ne smemo uzeti običnu PONUDU kao cenu.
    # Tražimo samo tekst koji ukazuje
    # da je trgovanje ZAISTA realizovano.

    obrasci = [

        (
            r"soj"
            r".{0,1500}?"
            r"trgovalo se"
            r".{0,300}?"
            r"(?:po|od)\s*"
            r"(\d+,\d+)\s*din/kg"
        ),

        (
            r"soj"
            r".{0,1500}?"
            r"ugovor"
            r".{0,300}?"
            r"(\d+,\d+)\s*din/kg"
        ),

        (
            r"soj"
            r".{0,1500}?"
            r"ponder(?:isana)? cena"
            r".{0,150}?"
            r"(\d+,\d+)"
        )
    ]

    return izvuci_prvi_broj(
        tekst,
        obrasci
    )


# =====================================
# GLAVNA FUNKCIJA
# =====================================

def uzmi_cene():

    izvestaji = pronadji_izvestaje()

    najnoviji = izvestaji[0]

    print("\nNAJNOVIJI IZVEŠTAJ:")
    print(najnoviji["naslov"])
    print(najnoviji["link"])


    # ---------------------------------
    # PŠENICA
    # ---------------------------------

    psenica = None
    psenica_period = None

    for izvestaj in izvestaji:

        cena = izvuci_psenicu(
            izvestaj["tekst"]
        )

        if cena is not None:

            psenica = cena
            psenica_period = izvestaj["period"]

            break


    # ---------------------------------
    # KUKURUZ
    # ---------------------------------

    kukuruz = None
    kukuruz_period = None

    for izvestaj in izvestaji:

        cena = izvuci_kukuruz(
            izvestaj["tekst"]
        )

        if cena is not None:

            kukuruz = cena
            kukuruz_period = izvestaj["period"]

            break


    # ---------------------------------
    # SOJA
    # ---------------------------------

    soja = None
    soja_period = None

    for izvestaj in izvestaji:

        cena = izvuci_soju(
            izvestaj["tekst"]
        )

        if cena is not None:

            soja = cena
            soja_period = izvestaj["period"]

            break


    cene = {
        "psenica": psenica,
        "kukuruz": kukuruz,
        "soja": soja
    }


    podaci_izvestaja = {

        "naslov": najnoviji["naslov"],

        "datum_objave": (
            najnoviji["datum"]
            .strftime("%d.%m.%Y")
        ),

        "link": najnoviji["link"],

        "psenica_period": psenica_period,
        "kukuruz_period": kukuruz_period,
        "soja_period": soja_period
    }


    print("\nIZVUČENE CENE:")
    print(cene)

    print("\nPERIODI POSLEDNJEG TRGOVANJA:")
    print(
        "Pšenica:",
        psenica_period
    )
    print(
        "Kukuruz:",
        kukuruz_period
    )
    print(
        "Soja:",
        soja_period
    )


    if all(
        vrednost is None
        for vrednost in cene.values()
    ):
        raise RuntimeError(
            "Nije pronađena nijedna realizovana cena."
        )


    return cene, podaci_izvestaja
