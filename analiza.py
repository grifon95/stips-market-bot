import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ==========================================================
# PODEŠAVANJA
# ==========================================================

BASE_URL = "https://nscomex.com"
ARHIVA_URL = "https://nscomex.com/category/nedeljni-izvestaj/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126 Safari/537.36"
    )
}


PROIZVODI = {
    "🌾 Pšenica": {
        "kolona": "psenica",
        "kljucevi": [
            "pšenic",
            "psenic",
            "hlebno zrno",
            "hlebnog zrna",
        ],
    },

    "🌽 Kukuruz": {
        "kolona": "kukuruz",
        "kljucevi": [
            "kukuruz",
        ],
    },

    "🫘 Soja": {
        "kolona": "soja",
        "kljucevi": [
            "soj",
        ],
    },
}


# ==========================================================
# POMOĆNE FUNKCIJE
# ==========================================================

def normalizuj_tekst(tekst):

    tekst = tekst.replace("\xa0", " ")

    tekst = re.sub(
        r"\s+",
        " ",
        tekst
    )

    return tekst.strip()


def broj_procenta(vrednost):

    return float(
        vrednost
        .replace(",", ".")
    )


# ==========================================================
# PRONAĐI NAJNOVIJI IZVEŠTAJ
# ==========================================================

def pronadji_najnoviji_izvestaj():

    response = requests.get(
        ARHIVA_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    kandidati = []


    for a in soup.find_all(
        "a",
        href=True
    ):

        href = urljoin(
            BASE_URL,
            a["href"]
        )


        rezultat = re.search(
            r"/nedeljni-izvestaj/"
            r"(\d+)-",
            href
        )


        if not rezultat:
            continue


        broj_izvestaja = int(
            rezultat.group(1)
        )


        kandidati.append(
            (
                broj_izvestaja,
                href
            )
        )


    if not kandidati:

        raise RuntimeError(
            "Analiza: nije pronađen "
            "najnoviji izveštaj Produktne berze."
        )


    kandidati.sort(
        key=lambda x: x[0],
        reverse=True
    )


    broj_izvestaja, link = (
        kandidati[0]
    )


    return (
        broj_izvestaja,
        link
    )


# ==========================================================
# PRONAĐI PASUS ZA ROBU
# ==========================================================

def pronadji_pasuse_robe(
    soup,
    kljucevi
):

    pasusi = []


    for p in soup.find_all("p"):

        tekst = normalizuj_tekst(
            p.get_text(
                " ",
                strip=True
            )
        )


        mali = tekst.lower()


        if any(
            kljuc in mali
            for kljuc in kljucevi
        ):

            pasusi.append(
                tekst
            )


    return pasusi


# ==========================================================
# IZVLAČENJE ZVANIČNOG PROCENTA
# ==========================================================

def procenat_iz_teksta(tekst):

    """
    Ovde NE uzimamo svaki broj uz znak %.

    To je veoma važno jer u izveštaju može da piše:

        pšenica sa min. 16% proteina

    To NIJE promena cene.

    Procenat prihvatamo samo ako je vezan za:
        rast
        porast
        povećanje
        više
        pad
        smanjenje
        manje
    """

    tekst = normalizuj_tekst(
        tekst
    )


    # ==================================================
    # RAST
    #
    # Primeri:
    #
    # rast od 1,13%
    # rast cene za 2,51%
    # porast od 1,20%
    # povećanje cene za 0,80%
    # ==================================================

    obrasci_rast = [

        (
            r"(?:rast|porast|povećanje|povecanje)"
            r"[^.!?%]{0,160}?"
            r"(?:od|za)?\s*"
            r"\(?\+?"
            r"(\d+(?:[.,]\d+)?)"
            r"\s*%"
        ),

        (
            r"\+"
            r"(\d+(?:[.,]\d+)?)"
            r"\s*%"
        ),
    ]


    for obrazac in obrasci_rast:

        rezultat = re.search(
            obrazac,
            tekst,
            flags=re.IGNORECASE
        )


        if rezultat:

            vrednost = broj_procenta(
                rezultat.group(1)
            )

            return abs(vrednost)


    # ==================================================
    # PAD
    #
    # Primeri:
    #
    # pad od 2,02%
    # smanjenje za 1,39%
    # ==================================================

    obrasci_pad = [

        (
            r"(?:pad|smanjenje)"
            r"[^.!?%]{0,160}?"
            r"(?:od|za)?\s*"
            r"\(?-?"
            r"(\d+(?:[.,]\d+)?)"
            r"\s*%"
        ),

        (
            r"-"
            r"(\d+(?:[.,]\d+)?)"
            r"\s*%"
        ),
    ]


    for obrazac in obrasci_pad:

        rezultat = re.search(
            obrazac,
            tekst,
            flags=re.IGNORECASE
        )


        if rezultat:

            vrednost = broj_procenta(
                rezultat.group(1)
            )

            return -abs(vrednost)


    # ==================================================
    # "ZA X% VIŠE"
    #
    # #85 pšenica:
    #
    # "što je za 0,42% više u odnosu..."
    # ==================================================

    rezultat = re.search(
        r"(?:za\s*)?"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*%\s*"
        r"(?:više|vise)",
        tekst,
        flags=re.IGNORECASE
    )


    if rezultat:

        vrednost = broj_procenta(
            rezultat.group(1)
        )

        return abs(vrednost)


    # ==================================================
    # "ZA X% MANJE"
    # ==================================================

    rezultat = re.search(
        r"(?:za\s*)?"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*%\s*"
        r"manje",
        tekst,
        flags=re.IGNORECASE
    )


    if rezultat:

        vrednost = broj_procenta(
            rezultat.group(1)
        )

        return -abs(vrednost)


    return None


# ==========================================================
# ZVANIČNE PROMENE IZ NAJNOVIJEG IZVEŠTAJA
# ==========================================================

def uzmi_zvanicne_promene():

    promene = {
        "psenica": None,
        "kukuruz": None,
        "soja": None,
    }


    try:

        broj_izvestaja, link = (
            pronadji_najnoviji_izvestaj()
        )


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


        print(
            "\nZVANIČNI PROCENTI:"
        )

        print(
            "Izveštaj:",
            f"#{broj_izvestaja}"
        )

        print(
            "Link:",
            link
        )


        for ime, podaci in (
            PROIZVODI.items()
        ):

            kolona = podaci["kolona"]

            pasusi = pronadji_pasuse_robe(
                soup,
                podaci["kljucevi"]
            )


            pronadjen = None


            for pasus in pasusi:

                procenat = procenat_iz_teksta(
                    pasus
                )


                if procenat is not None:

                    # ----------------------------------
                    # Zaštita od očigledno pogrešnog
                    # procenta.
                    # ----------------------------------

                    if abs(procenat) >= 15:

                        print(
                            f"{ime}: "
                            "sumnjiv zvanični procenat "
                            f"{procenat:+.2f}% — "
                            "ne koristim ga."
                        )

                        continue


                    pronadjen = procenat

                    break


            promene[kolona] = (
                pronadjen
            )


            if pronadjen is None:

                print(
                    f"{ime}: "
                    "zvanična promena nije pronađena "
                    "→ koristiće se CSV."
                )

            else:

                print(
                    f"{ime}: "
                    f"{pronadjen:+.2f}%"
                )


    except Exception as greska:

        # ==================================================
        # VEOMA VAŽNO
        #
        # Ako sajt privremeno ne radi ili se promeni HTML,
        # ANALIZA NE PADA.
        #
        # Jednostavno nastavljamo sa starim CSV obračunom.
        # ==================================================

        print(
            "\n⚠️ Zvanični procenti trenutno "
            "nisu mogli biti pročitani."
        )

        print(
            "Razlog:",
            greska
        )

        print(
            "Koristi se CSV obračun kao rezerva."
        )


    return promene


# ==========================================================
# GLAVNA ANALIZA
# ==========================================================

def napravi_analizu():

    fajl = "istorija_cena.csv"

    df = pd.read_csv(
        fajl
    )


    print(
        "\n================"
    )

    print(
        " STIPS ANALIZA "
    )

    print(
        "================"
    )


    if len(df) < 2:

        return (
            "Nema dovoljno podataka "
            "za analizu"
        )


    poslednja = df.iloc[-1]

    prethodna = df.iloc[-2]


    # ==================================================
    # SIGURNOSNI OPSEZI
    # ==================================================

    opsezi = {
        "psenica": (
            10,
            40
        ),

        "kukuruz": (
            10,
            40
        ),

        "soja": (
            30,
            100
        )
    }


    proizvodi = {
        "🌾 Pšenica":
            "psenica",

        "🌽 Kukuruz":
            "kukuruz",

        "🫘 Soja":
            "soja"
    }


    # ==================================================
    # PROVERA CENA
    # ==================================================

    for ime, kolona in (
        proizvodi.items()
    ):

        nova = poslednja[
            kolona
        ]


        if pd.isna(nova):

            raise RuntimeError(
                f"{ime}: "
                "nova cena nije pronađena."
            )


        nova = float(
            nova
        )


        minimum, maksimum = (
            opsezi[kolona]
        )


        if (
            nova < minimum
            or nova > maksimum
        ):

            raise RuntimeError(
                f"{ime}: "
                f"sumnjiva cena "
                f"{nova:.2f} din/kg. "
                f"Dozvoljeni sigurnosni "
                f"opseg je "
                f"{minimum}-{maksimum} "
                f"din/kg. "
                f"Moguća parser greška."
            )


    # ==================================================
    # UZIMAMO ZVANIČNE PROCENTE
    # ==================================================

    zvanicne_promene = (
        uzmi_zvanicne_promene()
    )


    poruka = (
        "📊 STIPS MARKET ANALIZA\n\n"
    )


    # ==================================================
    # ANALIZA
    # ==================================================

    for ime, kolona in (
        proizvodi.items()
    ):

        stara = prethodna[
            kolona
        ]

        nova = poslednja[
            kolona
        ]


        if (
            pd.isna(stara)
            or pd.isna(nova)
        ):

            continue


        stara = float(
            stara
        )

        nova = float(
            nova
        )


        if stara <= 0:

            raise RuntimeError(
                f"{ime}: "
                "prethodna cena nije validna."
            )


        # ==================================================
        # MATEMATIČKA PROMENA IZ CSV-a
        #
        # Ovo i dalje računamo zbog SIGURNOSTI.
        # ==================================================

        csv_promena = (
            (
                nova - stara
            )
            / stara
        ) * 100


        # ==================================================
        # ZAŠTITA OD PARSER GREŠKE
        #
        # OVA PROVERA OSTAJE NA CSV CENAMA.
        #
        # Čak i ako zvanični procenat izgleda normalno,
        # pogrešna cena ne sme proći.
        # ==================================================

        if abs(csv_promena) >= 15:

            raise RuntimeError(
                f"{ime}: "
                "detektovana sumnjiva "
                f"promena od "
                f"{csv_promena:.2f}% "
                f"({stara:.2f} -> "
                f"{nova:.2f} din/kg). "
                "Moguća parser greška. "
                "Automatski izveštaj "
                "nije poslat."
            )


        # ==================================================
        # KOJI PROCENAT PRIKAZUJEMO?
        # ==================================================

        zvanicna = (
            zvanicne_promene.get(
                kolona
            )
        )


        if zvanicna is not None:

            promena = zvanicna

            izvor_promene = (
                "zvanični izveštaj"
            )

        else:

            promena = csv_promena

            izvor_promene = (
                "CSV obračun"
            )


        # ==================================================
        # DEBUG
        #
        # U GitHub logu ćeš videti oba broja.
        # Telegram ostaje čist.
        # ==================================================

        print(
            f"\n{ime}"
        )

        print(
            "Cena:",
            f"{nova:.2f}"
        )

        print(
            "CSV promena:",
            f"{csv_promena:+.2f}%"
        )

        if zvanicna is not None:

            print(
                "Zvanična promena:",
                f"{zvanicna:+.2f}%"
            )

        else:

            print(
                "Zvanična promena: "
                "nije objavljena/pronađena"
            )


        print(
            "Za Telegram koristim:",
            izvor_promene
        )


        # ==================================================
        # SIGNAL
        # ==================================================

        if promena >= 5:

            signal = (
                "🔴 VELIKI RAST - "
                "pratiti prodaju"
            )

        elif promena <= -5:

            signal = (
                "🟢 PAD CENE - "
                "moguće kupovanje"
            )

        else:

            signal = (
                "🟡 STABILNO"
            )


        poruka += f"""
{ime}

Cena: {nova:.2f} din/kg
Promena: {promena:+.2f}%

Signal:
{signal}

"""


    print(
        "\n✅ Sigurnosna provera "
        "cena prošla."
    )


    return poruka
