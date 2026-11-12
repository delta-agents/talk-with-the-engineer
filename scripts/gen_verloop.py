"""Genereert de twee verlopen die boven de tijdbalken van `⟳` staan.

Twee compacte grafiekjes uit dezelfde rekenkern als de animaties ernaast, en ze
delen hun x-as met de tijdbalk eronder: de dagteller die daar loopt is dus ook
de leeswijzer van de grafiek.

* NAT   een neerslag-afvoergrafiek. De neerslag hangt omgekeerd aan de bovenrand
        [mm/dag], de afvoer van het land staat er onder [l/s/ha], en daartussen
        zit de vertraging die de afvoercurve maakt. De gemaalcapaciteit ligt er
        als streeplijn overheen: wat daarboven uitkomt, blijft in de polder.
* DROOG de spiegel. Geen vertraging maar een optelsom: het neerslagtekort loopt
        van de bovenrand af naar beneden, en de eigen voorraad van de polder is
        de dunne lijn die na tien dagen vlak wordt. Het gat ertussen is wat er
        van buiten moet komen.

Uitvoer gaat naar stdout en hoort in `topdownNat` en `topdownDroog` in teken/polder.js, tussen
de GEGENEREERD-bakens.
"""

import sys

sys.path.insert(0, "src")


# Het kader deelt zijn breedte met de tijdbalk eronder; zie `topdownNat`.
X0, X1 = 570.0, 830.0
NAT_TOP, NAT_BOD = 30.0, 150.0
DROOG_TOP, DROOG_BOD = 282.0, 402.0
SCHEIDING = 0.44  # waar in het natte kader de neerslag ophoudt en de afvoer begint

REGEN_AS = 32.0  # mm/dag op de volle hoogte van de neerslagband
AFVOER_AS = 3.5  # l/s/ha op de volle hoogte van de afvoerband
TEKORT_AS = 300.0  # mm over de volle hoogte van het droge kader

SEIZOEN_DAGEN = 183
REGIO, SCENARIO, HERHAALTIJD = "Aa_en_Maas", "Referentie", 10
