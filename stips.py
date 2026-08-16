import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://nscomex.com"
ARHIVA_URL = "https://nscomex.com/category/nedeljni-izvestaj/"

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


def izvuci_broj(tekst, obrasci):
    for obrazac in obrasci:

        rezultat = re.search(
            obrazac,
            tekst,
            flags=re.IGNORECASE
        )

        if rezultat:
            return broj(rezultat.group(1))

    return None


# ==========================================
# PRONALAZAK POSLEDNJIH IZVEŠTAJA
# ==========================================

def pronadji_izvestaje():

    linkovi = []
    vidjeni = set()

    # pregledamo više strana arhive
    for stranica in range(1, 5):

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

        for element in soup.find_all("a", href=True):

            href = urljoin(
                BASE_URL,
                element["href"]
            )

            if not re.search(
                r"/nedeljni-izvestaj/\d+-",
                href
            ):
                continue

            if href in vidjeni:
                continue

            vidjeni.add(href)
            linkovi.append(href)

    if not linkovi:
        raise RuntimeError(
            "Nisu pronađeni izveštaji Produktne berze."
        )

    izvestaji = []

    for link in linkovi:

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

        h1 = soup.find("h1")

        if not h1:
            continue

        naslov = normalizuj_tekst(
            h1.get_text(" ", strip=True)
        )

        rezultat = re.search(
            r"#(\d+)\s*\("
            r"(\d{2})\.(\d{2})"
            r"-(\d{2})\.(\d{2})\.(\d{4})",
            naslov
        )

        if not rezultat:
            continue

        broj_izvestaja = int(
            rezultat.group(1)
        )

        dan1 = rezultat.group(2)
        mesec1 = rezultat.group(3)

        dan2 = rezultat.group(4)
        mesec2 = rezultat.group(5)

        godina = rezultat.group(6)

        period = (
            f"{dan1}.{mesec1}."
            f"-{dan2}.{mesec2}.{godina}."
        )

        datum = datetime(
            int(godina),
            int(mesec2),
            int(dan2)
        )

        # BITNO:
        # Čuvamo PASUSE odvojeno.
        pasusi = []

        for p in soup.find_all("p"):

            tekst = normalizuj_tekst(
                p.get_text(" ", strip=True)
            )

            if tekst:
                pasusi.append(tekst)

        izvestaji.append({
            "broj": broj_izvestaja,
            "period": period,
            "datum": datum,
            "naslov": naslov,
            "link": link,
            "pasusi": pasusi
        })

    if not izvestaji:
        raise RuntimeError(
            "Izveštaji postoje, ali nisu mogli biti obrađeni."
        )

    izvestaji.sort(
        key=lambda x: (
            x["datum"],
            x["broj"]
        ),
        reverse=True
    )

    return izvestaji


# ==========================================
# PŠENICA
# ==========================================

def psenica_iz_izvestaja(izvestaj):

    for pasus in izvestaj["pasusi"]:

        mali = pasus.lower()

        if (
            "pšenic" not in mali
            and "psenic" not in mali
        ):
            continue

        cena = izvuci_broj(
            pasus,
            [
                (
                    r"pšenicom se trgovalo "
                    r"po ceni od\s*(\d+,\d+)"
                ),
                (
                    r"ponder cena iznosila je\s*"
                    r"(\d+,\d+)"
                ),
                (
                    r"prosečna cena hlebnog zrna "
                    r"iznosila je\s*(\d+,\d+)"
                ),
                (
                    r"prosečna cena pšenice "
                    r"iznosila je\s*(\d+,\d+)"
                )
            ]
        )

        if cena is not None:
            return cena

    return None


# ==========================================
# KUKURUZ
# ==========================================

def kukuruz_iz_izvestaja(izvestaj):

    for pasus in izvestaj["pasusi"]:

        if "kukuruz" not in pasus.lower():
            continue

        cena = izvuci_broj(
            pasus,
            [
                (
                    r"prosečna cena iznosila je\s*"
                    r"(\d+,\d+)"
                ),
                (
                    r"ponder cena iznosila je\s*"
                    r"(\d+,\d+)"
                ),
                (
                    r"prometovana cena kukuruza"
                    r".*?iznosila je\s*(\d+,\d+)"
                )
            ]
        )

        if cena is not None:
            return cena

    return None


# ==========================================
# SOJA
# ==========================================

def soja_iz_izvestaja(izvestaj):

    for pasus in izvestaj["pasusi"]:

        mali = pasus.lower()

        if (
            "soj" not in mali
        ):
            continue

        # Ako eksplicitno piše da trgovanja
        # nije bilo, NE UZIMAMO ponudu/tražnju.
        if (
            "trgovanje je izostalo" in mali
            or "trgovanje izostalo" in mali
            or "izostanak prometa" in mali
            or "nije došlo do trgovanja" in mali
        ):
            continue

        cena = izvuci_broj(
            pasus,
            [
                (
                    r"ovom uljaricom trgovalo se "
                    r"na jedinstvenom cenovnom nivou od\s*"
                    r"(\d+,\d+)"
                ),
                (
                    r"sojin.*?trgovalo se.*?"
                    r"(\d+,\d+)\s*din/kg"
                ),
                (
                    r"trgovana cena sojinog zrna "
                    r"iznosila je\s*(\d+,\d+)"
                ),
                (
                    r"ponder cena iznosila je\s*"
                    r"(\d+,\d+)"
                )
            ]
        )

        if cena is not None:
            return cena

    return None


# ==========================================
# GLAVNA FUNKCIJA
# ==========================================

def uzmi_cene():

    izvestaji = pronadji_izvestaje()

    najnoviji = izvestaji[0]

    print("\nNAJNOVIJI IZVEŠTAJ:")
    print(najnoviji["naslov"])
    print(najnoviji["link"])


    # PŠENICA
    psenica = None
    psenica_period = None

    for izvestaj in izvestaji:

        cena = psenica_iz_izvestaja(
            izvestaj
        )

        if cena is not None:

            psenica = cena
            psenica_period = izvestaj["period"]

            break


    # KUKURUZ
    kukuruz = None
    kukuruz_period = None

    for izvestaj in izvestaji:

        cena = kukuruz_iz_izvestaja(
            izvestaj
        )

        if cena is not None:

            kukuruz = cena
            kukuruz_period = izvestaj["period"]

            break


    # SOJA
    soja = None
    soja_period = None

    for izvestaj in izvestaji:

        cena = soja_iz_izvestaja(
            izvestaj
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
        "datum_objave": najnoviji["period"],
        "link": najnoviji["link"],

        "psenica_period": psenica_period,
        "kukuruz_period": kukuruz_period,
        "soja_period": soja_period
    }


    print("\nIZVUČENO:")
    print(cene)

    print("\nPERIOD POSLEDNJEG TRGOVANJA:")

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
