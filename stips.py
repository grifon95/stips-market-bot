import requests
import re


def uzmi_cene():

    url = "https://www.stips.minpolj.gov.rs/srl/vest/promet-robe-na-produktnoj-berzi-od-6-do-10-jula-2026-godine"


    response = requests.get(url)

    print("STIPS STATUS:", response.status_code)


    tekst = response.text


    # PŠENICA
    psenica = re.search(
        r"Prosečna cena iznosila je (\d+,\d+)",
        tekst
    )


    # KUKURUZ
    kukuruz = re.search(
        r"Ponder cena iznosila je (\d+,\d+)",
        tekst
    )


    # SOJA
    soja = re.search(
        r"sojino zrno.*?(\d+,\d+)",
        tekst,
        re.IGNORECASE
    )


    def broj(x):

        if x:
            return float(x.group(1).replace(",", "."))
        else:
            return None


    cene = {

        "psenica": broj(psenica),
        "kukuruz": broj(kukuruz),
        "soja": broj(soja)

    }


    print("IZVUČENO:")
    print(cene)


    return cene
