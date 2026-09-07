"""Reproduceert de voorkeursvolgorde op de laatste demo-beat van de presentatie.

Stelt één eis - de piek onder 18 cm op de referentiepolder - en legt hem langs
het hele natte rooster dat de statistiek kan trekken: elke terugkeertijd, elk
buiduur, beide seizoenen en elk regime. Per bedreiging zoekt de pakketzoeker het
goedkoopste pakket, en `core/preference.py` telt in hoeveel van die pakketten
elke maatregel voorkomt.

Dat is de heen-en-weer-vraag van de deck. Heen levert één pakket bij één bui;
pas door dezelfde eis tegen alle bedreigingen te leggen valt te zien welke
maatregel je vrijwel altijd nodig hebt en welke een keuze blijft. Het gemaal
staat in vrijwel elk antwoord, retentie in twee van de drie, en bergen en
peilopzet koopt hij bij deze eis nooit.

Het rooster is 312 doorrekeningen en duurt een paar minuten. Print eerst de
handvol bedreigingen die op het scherm staan, dan de telling over alles.
"""

import sys

sys.path.insert(0, "src")
from talk_with_the_engineer.core.package import Constraints
from talk_with_the_engineer.core.preference import (
    measures_in_the_cheapest_package,
    optimize,
    over_the_grid,
    storm_grid,
)
from talk_with_the_engineer.core.reference import (
    REFERENCE_POLDER,
    REFERENCE_STORM,
    storm_with,
)

RETURN_PERIODS = [
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    25.0,
    50.0,
    100.0,
    200.0,
    250.0,
    500.0,
    1000.0,
]
LENGTH_EVENT_HRS = [48.0, 96.0, 192.0]
TIME_OF_YEAR = ["winter", "summer"]
RAINFALL_REGIMES = ["LL", "L", "R", "H"]

EENHEID = {
    "vasthouden": "ha",
    "bergen": "ha",
    "afvoeren": "m3/s",
    "aanvoeren": "m3/s",
    "peilopzet": "m",
}

state = REFERENCE_POLDER
eis = Constraints(max_dh_total_m=0.18)

OP_HET_SCHERM = [
    ("de bui van de demo: T10", {}),
    ("eens per 25 jaar", dict(return_period=25.0)),
    ("eens per 100 jaar", dict(return_period=100.0)),
]

print(f"{'bedreiging':24s} {'kosten':>10s}  pakket")
print("-" * 74)
for label, afwijkingen in OP_HET_SCHERM:
    bui = storm_with(**afwijkingen)
    inzet = measures_in_the_cheapest_package(state, bui, eis)
    tekst = ", ".join(f"{n} {h:.3g} {EENHEID[n]}" for n, h in inzet.items())
    kosten = optimize(state, bui, eis).best.cost
    print(f"{label:24s} {kosten / 1e6:7.2f} mln  {tekst or 'geen maatregel nodig'}")

voorkeur = over_the_grid(
    state,
    eis,
    storm_grid(
        REFERENCE_STORM,
        RETURN_PERIODS,
        LENGTH_EVENT_HRS,
        TIME_OF_YEAR,
        RAINFALL_REGIMES,
    ),
)

print(
    f"\n{voorkeur.threats} bedreigingen, "
    f"{voorkeur.threats_needing_a_measure} waarbij een maatregel nodig is\n"
)
for naam, aantal in voorkeur.ordered:
    print(
        f"  {naam:12s} in {aantal:4d} van de {voorkeur.threats_needing_a_measure} "
        f"pakketten  ({100 * voorkeur.share_of(naam):.0f} %)"
    )
