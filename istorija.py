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


        # proveravamo da li već postoji današnji datum
        if danas in stara["datum"].astype(str).values:

            print("⚠️ Već postoji podatak za danas:", danas)

            return stara


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


    print("✅ Nova cena sačuvana")

    return istorija
