import requests


URL = (
    "https://www.investing.com/indices/"
    "urea-granular-fob-us-gulf-futures-historical-data"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126 Safari/537.36"
    )
}


def test_cbot_izvor():

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    print("STATUS:", response.status_code)
    print("DUZINA:", len(response.text))

    if response.status_code != 200:
        raise RuntimeError(
            f"CBOT UREA izvor nije dostupan. "
            f"HTTP {response.status_code}"
        )

    print("✅ CBOT UREA izvor dostupan iz GitHub Actions.")

    return True
