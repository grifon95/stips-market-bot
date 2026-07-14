from datetime import datetime

from stips import uzmi_cene
from istorija import sacuvaj_cene


print("🚀 STIPS BOT START")


datum = datetime.now().strftime("%d.%m.%Y")


# uzimamo cene sa STIPS-a
cene = uzmi_cene()


# čuvamo u istoriju
istorija = sacuvaj_cene(cene)


print("\nISTORIJA:")
print(istorija)



poruka = f"""
📊 STIPS MARKET ALERT

Datum: {datum}

🌾 Pšenica:
{cene['psenica']} din/kg

🌽 Kukuruz:
{cene['kukuruz']} din/kg

🫘 Soja:
{cene['soja']} din/kg
"""


print("\nPORUKA:")
print(poruka)
