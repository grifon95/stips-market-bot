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


# ==================================================
# PRONALAZAK NEDELJNIH IZVEŠTAJA
# ==================================================

def pronadji_izvestaje():

    linkovi = []
    vidjeni = set()

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


# ==================================================
# PROVERA DA LI JE TRGOVANJE IZOSTALO
# ==================================================

def nema_trgovanja(pasus):

    mali = pasus.lower()

    izrazi = [
        "trgovanje je izostalo",
        "trgovanje izostalo",
        "trgovina je izostala",
        "trgovina nije realizovana",
        "nije došlo do trgovanja",
        "nije došlo do zaključenja",
        "zaključenje berzanskih ugovora izostalo",
        "izostanak trgovanja",
        "izostankom trgovanja",
        "izostankom trgovinskih aktivnosti"
    ]

    return any(
        izraz in mali
        for izraz in izrazi
    )


# ==================================================
# PŠENICA
# ==================================================

def psenica_iz_izvestaja(izvestaj):

    for pasus in izvestaj["pasusi"]:

        mali = pasus.lower()

        if (
            "pšenic" not in mali
            and "psenic" not in mali
            and "hlebno zrno" not in mali
        ):
            continue

        if nema_trgovanja(pasus):
            continue

        cena = izvuci_broj(
            pasus,
            [
                # #83
                r"ponder cena iznosi\s*(\d+,\d+)",

                # stariji izveštaji
                r"ponder cena iznosila je\s*(\d+,\d+)",

                r"pšenicom se trgovalo po ceni od\s*(\d+,\d+)",

                r"prosečna cena hlebnog zrna iznosila je\s*(\d+,\d+)",

                r"prosečna cena pšenice iznosila je\s*(\d+,\d+)",

                r"prosečna cena iznosila je\s*(\d+,\d+)"
            ]
        )

        if cena is not None:
            return cena

    return None


# ==================================================
# KUKURUZ
# ==================================================

def kukuruz_iz_izvestaja(izvestaj):

    for pasus in izvestaj["pasusi"]:

        mali = pasus.lower()

        if "kukuruz" not in mali:
            continue

        # Može pasus da kaže da jedna VRSTA kukuruza
        # nije trgovana, a druga jeste.
        # Zato prvo pokušavamo da pronađemo
        # REALIZOVANU cenu.

        cena = izvuci_broj(
            pasus,
            [
                # #83:
                # Zaključen je samo jedan berzanski ugovor
                # po ceni 19,80 ... što predstavlja ponder cenu
                (
                    r"zaključen.*?"
                    r"berzanski ugovor.*?"
                    r"po ceni\s*(\d+,\d+)"
                ),

                # #82
                r"prosečna cena iznosila je\s*(\d+,\d+)",

                # #81
                (
                    r"prometovana cena kukuruza.*?"
                    r"iznosila je\s*(\d+,\d+)"
                ),

                r"ponder cena iznosi\s*(\d+,\d+)",

                r"ponder cena iznosila je\s*(\d+,\d+)",

                (
                    r"kukuruzom se trgovalo.*?"
                    r"(\d+,\d+)\s*din"
                )
            ]
        )

        if cena is not None:
            return cena

    return None


# ==================================================
# SOJA
# ==================================================

def soja_iz_izvestaja(izvestaj):

    for pasus in izvestaj["pasusi"]:

        mali = pasus.lower()

        if "soj" not in mali:
            continue

        # Kod soje nikada ne uzimamo samo
        # ponudu ili tražnju kao tržišnu cenu.
        if nema_trgovanja(pasus):
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
                    r"sojin.*?"
                    r"trgovalo se.*?"
                    r"(\d+,\d+)\s*din"
                ),

                (
                    r"trgovana cena sojinog zrna "
                    r"iznosila je\s*(\d+,\d+)"
                ),

                (
                    r"kupoprodajni ugovori za sojino zrno "
                    r"zaključeni su po ceni od\s*(\d+,\d+)"
                ),

                (
                    r"za sojino zrno zaključen je.*?"
                    r"po ceni od\s*(\d+,\d+)"
                )
            ]
        )

        if cena is not None:
            return cena

    return None


# ==================================================
# DA LI SE ROBA POMINJE U IZVEŠTAJU
# ==================================================

def roba_se_pominje(izvestaj, kljucevi):

    for pasus in izvestaj["pasusi"]:

        mali = pasus.lower()

        if any(
            kljuc in mali
            for kljuc in kljucevi
        ):
            return True

    return False


# ==================================================
# GLAVNA FUNKCIJA
# ==================================================

def uzmi_cene():

    izvestaji = pronadji_izvestaje()

    najnoviji = izvestaji[0]

    print("\nNAJNOVIJI IZVEŠTAJ:")
    print(najnoviji["naslov"])
    print(najnoviji["link"])


    # ==================================================
    # PŠENICA — PRVO NAJNOVIJI IZVEŠTAJ
    # ==================================================

    psenica = psenica_iz_izvestaja(
        najnoviji
    )

    psenica_period = None

    if psenica is not None:

        psenica_period = najnoviji["period"]

    else:

        # Ako se pšenica pominje u najnovijem izveštaju,
        # ali parser nije našao cenu, NE SMEMO tiho
        # uzeti staru cenu.
        if roba_se_pominje(
            najnoviji,
            ["pšenic", "psenic", "hlebno zrno"]
        ):

            raise RuntimeError(
                "Pšenica se nalazi u najnovijem "
                f"izveštaju #{najnoviji['broj']}, "
                "ali cena nije mogla biti pročitana. "
                "Parser treba proveriti."
            )

        # Samo ako se roba uopšte ne pominje,
        # tražimo poslednju realizovanu cenu.
        for izvestaj in izvestaji[1:]:

            cena = psenica_iz_izvestaja(
                izvestaj
            )

            if cena is not None:

                psenica = cena
                psenica_period = izvestaj["period"]
                break


    # ==================================================
    # KUKURUZ — PRVO NAJNOVIJI IZVEŠTAJ
    # ==================================================

    kukuruz = kukuruz_iz_izvestaja(
        najnoviji
    )

    kukuruz_period = None

    if kukuruz is not None:

        kukuruz_period = najnoviji["period"]

    else:

        if roba_se_pominje(
            najnoviji,
            ["kukuruz"]
        ):

            raise RuntimeError(
                "Kukuruz se nalazi u najnovijem "
                f"izveštaju #{najnoviji['broj']}, "
                "ali cena nije mogla biti pročitana. "
                "Parser treba proveriti."
            )

        for izvestaj in izvestaji[1:]:

            cena = kukuruz_iz_izvestaja(
                izvestaj
            )

            if cena is not None:

                kukuruz = cena
                kukuruz_period = izvestaj["period"]
                break


    # ==================================================
    # SOJA
    # ==================================================

    # Kod soje je drugačije:
    # ako nema realizovane trgovine u najnovijoj nedelji,
    # legitimno tražimo poslednju stvarno trgovanu cenu.

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
