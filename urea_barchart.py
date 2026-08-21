import requests


URL = "https://www.barchart.com/futures/quotes/JCQ26/overview"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126 Safari/537.36"
    )
}


def test_barchart():

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    print("STATUS:", response.status_code)
    print("DUZINA:", len(response.text))

    print("\nPRVIH 500 KARAKTERA:")
    print(response.text[:500])

    if response.status_code != 200:
        raise RuntimeError(
            f"Barchart nije dostupan iz GitHub Actions. "
            f"HTTP {response.status_code}"
        )

    if "JCQ26" not in response.text and "Urea" not in response.text:
        raise RuntimeError(
            "Stranica je otvorena, ali sadržaj JCQ26 nije pronađen."
        )

    print("\n✅ BARCHART JCQ26 JE DOSTUPAN")
