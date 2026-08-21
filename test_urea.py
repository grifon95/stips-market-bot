from urea import uzmi_ureu

podaci = uzmi_ureu()

print("\n====================")
print("UREA TEST")
print("====================")

print("Cena din/kg:", podaci["cena_din"])
print("Cena EUR/t:", podaci["cena_eur"])
print("Pakovanje:", podaci["pakovanje"])
print("Period:", podaci["period"])
print("Izveštaj:", podaci["izvestaj"])
print("Link:", podaci["link"])
