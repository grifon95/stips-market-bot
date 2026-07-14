import requests


def uzmi_cene():

    url = "https://www.stips.minpolj.gov.rs/srl/vest/promet-robe-na-produktnoj-berzi-od-6-do-10-jula-2026-godine"

    response = requests.get(url)

    print("STIPS STATUS:", response.status_code)

    tekst = response.text.lower()


    return {
        "psenica": "pronadjena stranica",
        "kukuruz": len(tekst),
        "soja": "ok"
    }
