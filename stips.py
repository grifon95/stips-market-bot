import re
import requests
from bs4 import BeautifulSoup


URL = "https://nscomex.com/podaci-iz-trgovanja/nedeljni-izvestaj/"

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

    return float(vrednost.replace(".", "").replace(",", "."))


def izvuci_prvi_broj(tekst, obrasci):

    for obrazac in obrasci:

        rezultat = re.search(
            obrazac,
            tekst,
            flags=re.IGNORECASE | re.DOTALL
        )

        if rezultat:
            return broj(rezultat.group(1))

    return None


def uzmi_izvestaje():

    response = requests.get(
        URL,
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

    # Odvajamo #82, #81, #80...
    delovi = re.split(
        r"(?=#\d+\s*\()",
        tekst
    )

    izvestaji = []

    for deo in delovi:

        rezultat = re.match(
            r"#(\d+)\s*"
            r"\((\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{4})\.\)",
            deo
        )

        if not rezultat:
            continue

        broj_izvestaja = int(rezultat.group(1))

        period = (
            rezultat.group(2)
            + "-"
            + rezultat.group(3)
        )

        izvestaji.append({
            "broj": broj_izvestaja,
            "period": period,
            "tekst": deo
        })

    if not izvestaji:
        raise RuntimeError(
            "Nisu pronađeni nedeljni izveštaji Produktne berze."
        )

    izvestaji.sort(
        key=lambda x: x["broj"],
        reverse=True
    )

    return izvestaji


def izvuci_psenicu(tekst):

    return izvuci_prvi_broj(
        tekst,
        [
            (
                r"pšenic.*?"
                r"ponder cena iznosila je\s*"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"pšenic.*?"
                r"prosečna cena.*?"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"pšenicom se trgovalo po ceni od\s*"
                r"(\d+,\d+)\s*din/kg"
            )
        ]
    )


def izvuci_kukuruz(tekst):

    return izvuci_prvi_broj(
        tekst,
        [
            (
                r"kukuruz.*?"
                r"prosečna cena iznosila je\s*"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"kukuruz.*?"
                r"ponder cena iznosila je\s*"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"prometovana cena kukuruza.*?"
                r"iznosila je\s*"
                r"(\d+,\d+)\s*din/kg"
            )
        ]
    )


def izvuci_soju(tekst):

    # samo REALIZOVANO trgovanje,
    # ne ponuda ili tražnja

    return izvuci_prvi_broj(
        tekst,
        [
            (
                r"soj.*?"
                r"trgovalo se.*?"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"trgovana cena sojinog zrna "
                r"iznosila je\s*"
                r"(\d+,\d+)\s*din/kg"
            ),
            (
                r"sojin.*?"
                r"berzanski ugovor.*?"
                r"(\d+,\d+)\s*din/kg"
            )
        ]
    )


def uzmi_cene():

    izvestaji = uzmi_izvestaje()

    najnoviji = izvestaji[0]

    print("NAJNOVIJI IZVEŠTAJ:")
    print(
        f"#{najnoviji['broj']} "
        f"({najnoviji['period']})"
    )


    # PŠENICA
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


    # KUKURUZ
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


    # SOJA
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
        "naslov": (
            f"Produktna berza "
            f"#{najnoviji['broj']} "
            f"({najnoviji['period']})"
        ),
        "datum_objave": najnoviji["period"],
        "link": URL,
        "psenica_period": psenica_period,
        "kukuruz_period": kukuruz_period,
        "soja_period": soja_period
    }


    print("\nIZVUČENO:")
    print(cene)

    print("\nPERIODI:")
    print("Pšenica:", psenica_period)
    print("Kukuruz:", kukuruz_period)
    print("Soja:", soja_period)


    if all(
        vrednost is None
        for vrednost in cene.values()
    ):
        raise RuntimeError(
            "Nije pronađena nijedna realizovana cena."
        )


    return cene, podaci_izvestaja
