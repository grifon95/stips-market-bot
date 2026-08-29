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


# ==========================================================
# PODEŠAVANJA
# ==========================================================

ROBE = {
    "psenica": {
        "naziv": "Pšenica",
        "kljucevi": [
            "pšenic",
            "psenic",
            "hlebno zrno",
            "hlebnog zrna",
        ],
        "min": 10.0,
        "max": 50.0,
    },

    "kukuruz": {
        "naziv": "Kukuruz",
        "kljucevi": [
            "kukuruz",
            "ove žitarice",
            "ove zitarice",
        ],
        "min": 10.0,
        "max": 50.0,
    },

    "soja": {
        "naziv": "Soja",
        "kljucevi": [
            "soj",
            "uljaric",
        ],
        "min": 30.0,
        "max": 100.0,
    },
}


# Reči koje ukazuju na REALIZOVANO trgovanje.
# Ovde se NE traži cela rečenica.
REALIZACIJA = (
    "trgovan",
    "trgovalo",
    "prometovan",
    "prometovana",
    "prometovano",
    "realizovan",
    "realizovana",
    "realizovano",
    "zaključen",
    "zaključeni",
    "zaključena",
    "zakljucen",
    "zakljuceni",
    "kupoprodajni ugovor",
    "berzanski ugovor",
)


# Posebno jaki pokazatelji da je u pitanju
# reprezentativna / nedeljna cena.
PONDER = (
    "ponder",
)

PROSEK = (
    "prosečna",
    "prosecna",
    "prosečni",
    "prosecni",
)


# Reči koje ukazuju da cena predstavlja samo
# ponudu ili tražnju, a NE realizovanu trgovinu.
PONUDA_TRAZNJA = (
    "tražnj",
    "traznj",
    "ponud",
    "nuđen",
    "nuden",
    "ponuđen",
    "ponudjen",
    "kupci nud",
    "prodavci traž",
    "prodavci traz",
)


NEMA_TRGOVANJA = (
    "trgovanje je izostalo",
    "trgovanje izostalo",
    "trgovina je izostala",
    "trgovina nije realizovana",
    "nije došlo do trgovanja",
    "nije doslo do trgovanja",
    "nije došlo do zaključenja",
    "nije doslo do zakljucenja",
    "zaključenje berzanskih ugovora izostalo",
    "zakljucenje berzanskih ugovora izostalo",
    "izostanak trgovanja",
    "izostankom trgovanja",
    "izostankom trgovinskih aktivnosti",
    "odsustvo iz trgovanja",
)


# Ključna stvar:
# tražimo BROJ DIREKTNO ISPRED:
#
#     din/kg bez PDV
#
# Tako nećemo uzeti cenu SA PDV-om.
CENA_BEZ_PDV_RE = re.compile(
    r"(?<!\d)"
    r"(\d{1,3}(?:[.,]\d{1,2})?)"
    r"\s*din\s*/\s*kg"
    r"\s*bez\s*PDV(?:-a)?",
    flags=re.IGNORECASE,
)


# ==========================================================
# POMOĆNE FUNKCIJE
# ==========================================================

def normalizuj_tekst(tekst):
    tekst = tekst.replace("\xa0", " ")
    tekst = re.sub(r"\s+", " ", tekst)
    return tekst.strip()


def broj(vrednost):
    """
    Podržava:
        19,40
        19.40
    """

    vrednost = vrednost.strip()

    if "," in vrednost:
        vrednost = vrednost.replace(".", "")
        vrednost = vrednost.replace(",", ".")
        return float(vrednost)

    return float(vrednost)


def sadrzi_neki(tekst, izrazi):
    mali = tekst.lower()

    return any(
        izraz in mali
        for izraz in izrazi
    )


def podeli_na_recenice(tekst):
    """
    Delimo paragraf na manje delove.

    Decimalni brojevi na sajtu koriste zarez,
    pa tačka normalno može da služi kao kraj rečenice.
    """

    tekst = normalizuj_tekst(tekst)

    return [
        deo.strip()
        for deo in re.split(r"(?<=[.!?])\s+", tekst)
        if deo.strip()
    ]


# ==========================================================
# DA LI JE BROJ DEO CENOVNOG RASPONA
# ==========================================================

def broj_je_deo_raspona(recenica, match):
    """
    Primer:

        od 19,20 do 19,30 din/kg

    Regex za cenu bi video 19,30 jer je direktno uz din/kg.

    Ali to NIJE ponder / prosečna cena.

    Zato proveravamo da li neposredno pre pronađenog broja
    postoji drugi broj + "do", "-", "–" ili "—".
    """

    pre_broja = recenica[:match.start()]

    obrazac = (
        r"\d{1,3}(?:[.,]\d{1,2})"
        r"\s*(?:do|-|–|—)\s*$"
    )

    return bool(
        re.search(
            obrazac,
            pre_broja,
            flags=re.IGNORECASE
        )
    )


# ==========================================================
# ANALIZA JEDNE CENE
# ==========================================================

def oceni_kandidata(recenica, match):
    """
    Ne zavisimo od jedne konkretne formulacije.

    Red prioriteta:

        PONDER
        PROSEČNA
        REALIZOVANA / TRGOVANA
        ostala pojedinačna cena

    Ponude i tražnje se odbacuju ako nema dokaza
    da je ugovor ZAISTA realizovan.
    """

    mali = recenica.lower()

    vrednost = broj(
        match.group(1)
    )

    # ------------------------------------------
    # 1. Cenovni raspon NE uzimamo kao cenu
    # ------------------------------------------

    if broj_je_deo_raspona(
        recenica,
        match
    ):
        return None


    ima_realizaciju = sadrzi_neki(
        recenica,
        REALIZACIJA
    )

    ima_ponudu_traznju = sadrzi_neki(
        recenica,
        PONUDA_TRAZNJA
    )

    nema_trgovanja = sadrzi_neki(
        recenica,
        NEMA_TRGOVANJA
    )


    # ------------------------------------------
    # 2. Samo ponuda/tražnja = NE
    # ------------------------------------------

    if (
        ima_ponudu_traznju
        and not ima_realizaciju
    ):
        return None


    # ------------------------------------------
    # 3. Rečenica kaže da nije trgovano
    # ------------------------------------------

    if (
        nema_trgovanja
        and not ima_realizaciju
    ):
        return None


    # ------------------------------------------
    # 4. Ocena kandidata
    # ------------------------------------------

    score = 20
    razlog = "pojedinačna cena"


    if sadrzi_neki(
        recenica,
        PONDER
    ):
        score = 100
        razlog = "ponder cena"

    elif sadrzi_neki(
        recenica,
        PROSEK
    ):
        score = 90
        razlog = "prosečna cena"

    elif ima_realizaciju:
        score = 80
        razlog = "realizovana/trgovana cena"

    elif "cena" in mali:
        score = 50
        razlog = "cena bez PDV-a"


    return {
        "cena": vrednost,
        "score": score,
        "razlog": razlog,
        "recenica": recenica,
    }


# ==========================================================
# ANALIZA PARAGRAFA ZA ROBU
# ==========================================================

def paragraf_pripada_robi(pasus, roba):
    mali = pasus.lower()

    return any(
        kljuc in mali
        for kljuc in ROBE[roba]["kljucevi"]
    )


def izvuci_kandidate(izvestaj, roba):

    kandidati = []

    pronadjen_pas = False
    pronadjeno_nema_trgovanja = False
    pronadjena_jedinica = False

    for pasus in izvestaj["pasusi"]:

        if not paragraf_pripada_robi(
            pasus,
            roba
        ):
            continue

        pronadjen_pas = True

        if sadrzi_neki(
            pasus,
            NEMA_TRGOVANJA
        ):
            pronadjeno_nema_trgovanja = True


        for recenica in podeli_na_recenice(
            pasus
        ):

            for match in CENA_BEZ_PDV_RE.finditer(
                recenica
            ):

                pronadjena_jedinica = True

                kandidat = oceni_kandidata(
                    recenica,
                    match
                )

                if kandidat is None:
                    continue

                cena = kandidat["cena"]

                minimum = ROBE[roba]["min"]
                maksimum = ROBE[roba]["max"]

                if not (
                    minimum
                    <= cena
                    <= maksimum
                ):
                    continue

                kandidati.append(
                    kandidat
                )


    return {
        "kandidati": kandidati,
        "roba_pomenuta": pronadjen_pas,
        "nema_trgovanja": pronadjeno_nema_trgovanja,
        "ima_din_kg": pronadjena_jedinica,
    }


# ==========================================================
# IZBOR NAJBOLJE CENE
# ==========================================================

def cena_robe_iz_izvestaja(
    izvestaj,
    roba
):

    analiza = izvuci_kandidate(
        izvestaj,
        roba
    )

    kandidati = analiza["kandidati"]

    if not kandidati:
        return None, analiza


    # Najjači kandidat prvi.
    kandidati.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    najbolji_score = kandidati[0]["score"]

    najbolji = [
        kandidat
        for kandidat in kandidati
        if kandidat["score"] == najbolji_score
    ]


    # Ako dva kandidata iste važnosti imaju
    # istu cenu, nema problema.
    jedinstvene_cene = sorted(
        set(
            kandidat["cena"]
            for kandidat in najbolji
        )
    )


    if len(jedinstvene_cene) == 1:

        izbor = najbolji[0]

        return izbor["cena"], {
            **analiza,
            "izbor": izbor,
        }


    # ------------------------------------------------------
    # VIŠE RAZLIČITIH PODJEDNAKO JAKIH CENA
    #
    # NE POGAĐAMO.
    # ------------------------------------------------------

    detalji = "\n".join(
        f"- {k['cena']}: {k['recenica']}"
        for k in najbolji
    )

    raise RuntimeError(
        f"{ROBE[roba]['naziv']}: "
        "pronađeno je više mogućih realizovanih cena "
        "iste važnosti.\n"
        "Bot namerno neće pogoditi cenu.\n"
        f"{detalji}"
    )


# ==========================================================
# PRONALAZAK IZVEŠTAJA
# ==========================================================

def pronadji_izvestaje():

    linkovi = []
    vidjeni = set()


    for stranica in range(1, 5):

        if stranica == 1:
            url = ARHIVA_URL
        else:
            url = (
                f"{ARHIVA_URL}"
                f"page/{stranica}/"
            )


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


        for element in soup.find_all(
            "a",
            href=True
        ):

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

            linkovi.append(
                href
            )


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
            h1.get_text(
                " ",
                strip=True
            )
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
                p.get_text(
                    " ",
                    strip=True
                )
            )

            if tekst:
                pasusi.append(
                    tekst
                )


        izvestaji.append({
            "broj": broj_izvestaja,
            "period": period,
            "datum": datum,
            "naslov": naslov,
            "link": link,
            "pasusi": pasusi,
        })


    if not izvestaji:

        raise RuntimeError(
            "Izveštaji postoje, "
            "ali nisu mogli biti obrađeni."
        )


    izvestaji.sort(
        key=lambda x: (
            x["datum"],
            x["broj"]
        ),
        reverse=True
    )


    return izvestaji


# ==========================================================
# POSLEDNJA REALIZOVANA CENA
# ==========================================================

def poslednja_realizovana_cena(
    izvestaji,
    roba
):

    for izvestaj in izvestaji:

        cena, analiza = cena_robe_iz_izvestaja(
            izvestaj,
            roba
        )


        if cena is None:
            continue


        return (
            cena,
            izvestaj["period"],
            izvestaj,
            analiza,
        )


    return (
        None,
        None,
        None,
        None,
    )


# ==========================================================
# GLAVNA FUNKCIJA
# ==========================================================

def uzmi_cene():

    izvestaji = pronadji_izvestaje()

    najnoviji = izvestaji[0]


    print("\nNAJNOVIJI IZVEŠTAJ:")
    print(najnoviji["naslov"])
    print(najnoviji["link"])


    rezultati = {}
    periodi = {}


    for roba in (
        "psenica",
        "kukuruz",
        "soja"
    ):

        naziv = ROBE[roba]["naziv"]


        # ----------------------------------------------
        # Prvo analiziramo NAJNOVIJI izveštaj
        # ----------------------------------------------

        cena_nova, analiza_nova = (
            cena_robe_iz_izvestaja(
                najnoviji,
                roba
            )
        )


        if cena_nova is not None:

            rezultati[roba] = cena_nova

            periodi[roba] = (
                najnoviji["period"]
            )


            izbor = analiza_nova.get(
                "izbor"
            )


            print(
                f"\n{naziv}: "
                f"{cena_nova:.2f}"
            )


            if izbor:

                print(
                    "Razlog:",
                    izbor["razlog"]
                )

                print(
                    "Iz rečenice:",
                    izbor["recenica"]
                )


            continue


        # ----------------------------------------------
        # NEMA realizovane cene u najnovijem izveštaju.
        #
        # Ako imamo:
        # - ponude
        # - tražnju
        # - cenovne raspone
        # - eksplicitno "trgovanje izostalo"
        #
        # NE UZIMAMO TE BROJEVE.
        #
        # Tražimo poslednju STVARNO realizovanu cenu.
        # ----------------------------------------------

        (
            stara_cena,
            stari_period,
            stari_izvestaj,
            stara_analiza,
        ) = poslednja_realizovana_cena(
            izvestaji[1:],
            roba
        )


        if stara_cena is None:

            raise RuntimeError(
                f"{naziv}: nije pronađena "
                "nijedna pouzdana realizovana cena "
                "u dostupnim izveštajima."
            )


        rezultati[roba] = stara_cena

        periodi[roba] = stari_period


        print(
            f"\n{naziv}: "
            f"nema pouzdane nove realizovane cene."
        )

        print(
            "Koristim poslednju realizovanu:",
            f"{stara_cena:.2f}"
        )

        print(
            "Period:",
            stari_period
        )

        print(
            "Izveštaj:",
            stari_izvestaj["naslov"]
        )


    # ==================================================
    # ZAVRŠNA SIGURNOSNA PROVERA
    # ==================================================

    for roba, cena in rezultati.items():

        minimum = ROBE[roba]["min"]
        maksimum = ROBE[roba]["max"]

        if cena is None:

            raise RuntimeError(
                f"{ROBE[roba]['naziv']}: "
                "cena je None."
            )


        if not (
            minimum
            <= cena
            <= maksimum
        ):

            raise RuntimeError(
                f"{ROBE[roba]['naziv']}: "
                f"sumnjiva cena {cena}. "
                "Bot je zaustavljen."
            )


    cene = {
        "psenica": rezultati["psenica"],
        "kukuruz": rezultati["kukuruz"],
        "soja": rezultati["soja"],
    }


    podaci_izvestaja = {

        "naslov":
            najnoviji["naslov"],

        "datum_objave":
            najnoviji["period"],

        "link":
            najnoviji["link"],

        "psenica_period":
            periodi["psenica"],

        "kukuruz_period":
            periodi["kukuruz"],

        "soja_period":
            periodi["soja"],
    }


    print("\n==============================")
    print("KONAČNO IZVUČENO")
    print("==============================")

    print(cene)


    print(
        "\nPERIOD POSLEDNJEG TRGOVANJA:"
    )

    print(
        "Pšenica:",
        periodi["psenica"]
    )

    print(
        "Kukuruz:",
        periodi["kukuruz"]
    )

    print(
        "Soja:",
        periodi["soja"]
    )


    print(
        "\n✅ Parser završio bez "
        "sigurnosnih grešaka."
    )


    return (
        cene,
        podaci_izvestaja
    )
