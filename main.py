from datetime import datetime
from stips import uzmi_cene


print("🚀 STIPS BOT START")


datum = datetime.now().strftime("%d.%m.%Y")


cene = uzmi_cene()


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


print(poruka)
