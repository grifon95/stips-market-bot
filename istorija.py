import pandas as pd
import os
from datetime import datetime


def sacuvaj_cene(cene):

    fajl = "istorija_cena.csv"


    novi = cene.copy()

    novi["datum"] = datetime.now().strftime("%d.%m.%Y")


    novi_red = pd.DataFrame([novi])


    if os.path.exists(fajl):

        stara = pd.read_csv(fajl)

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


    return istorija
