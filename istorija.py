import pandas as pd
import os
from datetime import datetime


def sacuvaj_cene(cene):

    fajl = "istorija_cena.csv"

    danas = datetime.now().strftime("%d.%m.%Y")

    novi = cene.copy()
    novi["datum"] = danas

    novi_red = pd.DataFrame([novi])


    if os.path.exists(fajl):

        stara = pd.read_csv(fajl)

        if "datum" not in stara.columns:
            raise RuntimeError(
                "istorija_cena.csv nema kolonu datum."
            )


        # =========================
        # AKO DANAS VEĆ POSTOJI
        # AŽURIRAJ GA
        # =========================

        maska = (
            stara["datum"]
            .astype(str)
            .eq(danas)
        )

        if maska.any():

            print(
                "🔄 Već postoji podatak za danas."
            )
            print(
                "Ažuriram ga najnovijim cenama:"
            )
            print(cene)

            # Ako slučajno postoji više redova
            # za isti datum, brišemo ih sve
            # i ostavljamo samo novi.
            stara = stara.loc[~maska]

            istorija = pd.concat(
                [stara, novi_red],
                ignore_index=True
            )

            istorija.to_csv(
                fajl,
                index=False
            )

            print(
                "✅ Današnji podatak ažuriran:",
                danas
            )

            return istorija


        # =========================
        # NOVI DAN
        # =========================

        istorija = pd.concat(
            [stara, novi_red],
            ignore_index=True
        )


    else:

        istorija = novi_red


    istorija.to_csv(
        fajl,
        index=False
    )


    print(
        "✅ Nova cena sačuvana:",
        danas
    )

    return istorija
