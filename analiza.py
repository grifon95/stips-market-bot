import pandas as pd


def napravi_analizu():

    fajl = "istorija_cena.csv"

    df = pd.read_csv(fajl)


    print("\n================")
    print(" STIPS ANALIZA ")
    print("================")


    if len(df) < 2:
        return "Nema dovoljno podataka za analizu"


    poslednja = df.iloc[-1]
    prethodna = df.iloc[-2]


    # =====================================
    # SIGURNOSNI OPSEZI
    # =====================================

    # Ovo nisu prognoze tržišta.
    # Služe samo da uhvate očiglednu parser grešku,
    # npr. soja = 18 din/kg.

    opsezi = {
        "psenica": (10, 40),
        "kukuruz": (10, 40),
        "soja": (30, 100)
    }


    proizvodi = {
        "🌾 Pšenica": "psenica",
        "🌽 Kukuruz": "kukuruz",
        "🫘 Soja": "soja"
    }


    # =====================================
    # PROVERA PODATAKA
    # =====================================

    for ime, kolona in proizvodi.items():

        nova = poslednja[kolona]

        if pd.isna(nova):
            raise RuntimeError(
                f"{ime}: nova cena nije pronađena."
            )

        nova = float(nova)

        minimum, maksimum = opsezi[kolona]

        if nova < minimum or nova > maksimum:
            raise RuntimeError(
                f"{ime}: sumnjiva cena {nova:.2f} din/kg. "
                f"Dozvoljeni sigurnosni opseg je "
                f"{minimum}-{maksimum} din/kg. "
                f"Moguća parser greška."
            )


    poruka = "📊 STIPS MARKET ANALIZA\n\n"


    # =====================================
    # ANALIZA PROMENA
    # =====================================

    for ime, kolona in proizvodi.items():

        stara = prethodna[kolona]
        nova = poslednja[kolona]


        if pd.isna(stara) or pd.isna(nova):
            continue


        stara = float(stara)
        nova = float(nova)


        if stara <= 0:
            raise RuntimeError(
                f"{ime}: prethodna cena nije validna."
            )


        promena = ((nova - stara) / stara) * 100


        # =================================
        # ZAŠTITA OD OGROMNE PROMENE
        # =================================

        # Ako bot odjednom izvuče npr.
        # soja 53.50 -> 18.00,
        # prekidamo slanje.

        if abs(promena) >= 15:

            raise RuntimeError(
                f"{ime}: detektovana sumnjiva promena "
                f"od {promena:.2f}% "
                f"({stara:.2f} -> {nova:.2f} din/kg). "
                f"Moguća parser greška. "
                f"Automatski izveštaj nije poslat."
            )


        # =================================
        # SIGNAL
        # =================================

        if promena >= 5:

            signal = (
                "🔴 VELIKI RAST - pratiti prodaju"
            )

        elif promena <= -5:

            signal = (
                "🟢 PAD CENE - moguće kupovanje"
            )

        else:

            signal = "🟡 STABILNO"


        poruka += f"""
{ime}

Cena: {nova:.2f} din/kg
Promena: {promena:+.2f}%

Signal:
{signal}

"""


    print("✅ Sigurnosna provera cena prošla.")

    return poruka
