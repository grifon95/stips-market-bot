import pandas as pd
import matplotlib.pyplot as plt


def napravi_grafikon():

    fajl = "istorija_cena.csv"

    df = pd.read_csv(fajl)


    plt.figure(figsize=(10,5))


    plt.plot(
        df["datum"],
        df["psenica"],
        marker="o",
        label="Pšenica"
    )

    plt.plot(
        df["datum"],
        df["kukuruz"],
        marker="o",
        label="Kukuruz"
    )

    plt.plot(
        df["datum"],
        df["soja"],
        marker="o",
        label="Soja"
    )


    plt.title("STIPS cene - istorija")

    plt.xlabel("Datum")

    plt.ylabel("Din/kg")


    plt.xticks(rotation=45)

    plt.legend()

    plt.tight_layout()


    ime = "grafikon_cena.png"


    plt.savefig(
        ime,
        dpi=300
    )


    plt.close()


    return ime
