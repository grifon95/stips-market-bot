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


    poruka = "📊 STIPS MARKET ANALIZA\n\n"


    proizvodi = {
        "🌾 Pšenica": "psenica",
        "🌽 Kukuruz": "kukuruz",
        "🫘 Soja": "soja"
    }


    for ime, kolona in proizvodi.items():

        stara = prethodna[kolona]
        nova = poslednja[kolona]


        if pd.isna(stara) or pd.isna(nova):
            continue


        promena = ((nova - stara) / stara) * 100


        if promena >= 5:
            signal = "🔴 VELIKI RAST - pratiti prodaju"

        elif promena <= -5:
            signal = "🟢 PAD CENE - moguće kupovanje"

        else:
            signal = "🟡 STABILNO"


        poruka += f"""
{ime}

Cena: {nova} din/kg
Promena: {promena:.2f}%

Signal:
{signal}

"""


    return poruka
