import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


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


def pronadji_izvestaje():

    linkovi = []
    vidjeni = set()

    # Idemo dovoljno unazad da pronađemo poslednju UREA trgovinu
    for stranica in range(1, 8):

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

        except requests.RequestException:
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
            "naslov": naslov,
            "link": link,
            "pasusi": pasusi
        })

    izvestaji.sort(
        key=lambda x: x["broj"],
        reverse=True
    )

    return izvestaji


def izvuci_ureu(izvestaj):

    for pasus in izvestaj["pasusi"]:

        mali = pasus.lower()

        if "urea" not in mali:
            continue

        # Ne uzimamo običnu ponudu/tražnju.
        # Mora da postoji jasan signal da je trgovanje realizovano.
        if not any(
            izraz in mali
            for izraz in [
                "prometovana je urea",
                "prometovana urea",
                "ugovor zaključen",
                "kupoprodajni ugovor",
                "trgovalo se",
            ]
        ):
            continue

        cena_din = re.search(
            r"(\d+,\d+)\s*din/kg",
            pasus,
            flags=re.IGNORECASE
        )

        cena_eur = re.search(
            r"\(?\s*(\d+(?:,\d+)?)\s*eur/t",
            pasus,
            flags=re.IGNORECASE
        )

        pakovanje = re.search(
            r"pakovanj\w*\s*(\d+/\d+)",
            pasus,
            flags=re.IGNORECASE
        )

        if not cena_din:
            continue

        return {
            "cena_din": broj(cena_din.group(1)),
            "cena_eur": (
                broj(cena_eur.group(1))
                if cena_eur
                else None
            ),
            "pakovanje": (
                pakovanje.group(1)
                if pakovanje
                else "nije navedeno"
            )
        }

    return None


def uzmi_ureu():

    izvestaji = pronadji_izvestaje()

    for izvestaj in izvestaji:

        rezultat = izvuci_ureu(
            izvestaj
        )

        if rezultat is not None:

            podaci = {
                "cena_din": rezultat["cena_din"],
                "cena_eur": rezultat["cena_eur"],
                "pakovanje": rezultat["pakovanje"],
                "period": izvestaj["period"],
                "izvestaj": izvestaj["naslov"],
                "link": izvestaj["link"]
            }

            print("\nPOSLEDNJA UREA TRGOVINA:")
            print(podaci)

            return podaci

    raise RuntimeError(
        "Nije pronađena poslednja realizovana UREA cena."
    )
