"""Reproduceert de voorkeursvolgorde op de laatste demo-beat van de presentatie.

Stelt één eis - de piek onder 18 cm op de referentiepolder - en legt hem langs
het hele natte rooster dat de statistiek kan trekken: elke terugkeertijd, elk
buiduur, beide seizoenen en elk regime. Per bedreiging zoekt de pakketzoeker het
goedkoopste pakket, en dit script telt in hoeveel van die pakketten elke
maatregel voorkomt.

Dat is de heen-en-weer-vraag van de deck. Heen levert één pakket bij één bui;
pas door dezelfde eis tegen alle bedreigingen te leggen valt te zien welke
maatregel je vrijwel altijd nodig hebt en welke een keuze blijft. Het gemaal
staat in vrijwel elk antwoord, retentie in twee van de drie, en bergen en
peilopzet koopt hij bij deze eis nooit.

Het rooster is 312 doorrekeningen en duurt een paar minuten. Print eerst de
handvol bedreigingen die op het scherm staan, dan de telling over alles.
"""

import collections
import itertools
import sys

sys.path.insert(0, "src")
from talk_with_the_engineer.core.connection import (
    single_pump_connection,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.package import (
    Constraints,
    optimize,
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


class Bui:
    """De referentiebui: acht dagen, herhaaltijd tien jaar, zomer, regime R."""

    return_period = 10.0
    time_of_year = "summer"
    length_event_hrs = 192.0
    rainfall_regime = "R"
    name_rainfall_pattern = "p1c"
    days_to_discharge = 2


def bui(**afwijkingen):
    """De referentiebui met een paar velden anders - één bedreiging dus."""
    b = Bui()
    for veld, waarde in afwijkingen.items():
        setattr(b, veld, waarde)
    return b


# De referentiepolder: 1000 ha, 5 % open water, gemaal 1,5 m3/s.
state = PolderState(
    area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
)
eis = Constraints(max_dh_total_m=0.18)


def pakket(b):
    """Het goedkoopste pakket bij deze bui, als tekst en als verzameling."""
    p = optimize(state, b, eis).best
    inzet = {naam: hoeveel for naam, hoeveel in p.quantities.items() if hoeveel > 1e-9}
    tekst = ", ".join(f"{n} {h:.3g} {EENHEID[n]}" for n, h in inzet.items())
    return inzet, tekst or "geen maatregel nodig", p.cost


OP_HET_SCHERM = [
    ("de bui van de demo: T10", {}),
    ("eens per 25 jaar", dict(return_period=25.0)),
    ("eens per 100 jaar", dict(return_period=100.0)),
]

print(f"{'bedreiging':24s} {'kosten':>10s}  pakket")
print("-" * 74)
for label, afwijkingen in OP_HET_SCHERM:
    _, tekst, kosten = pakket(bui(**afwijkingen))
    print(f"{label:24s} {kosten / 1e6:7.2f} mln  {tekst}")

telling = collections.Counter()
met_maatregel = 0
rooster = itertools.product(
    RETURN_PERIODS, LENGTH_EVENT_HRS, TIME_OF_YEAR, RAINFALL_REGIMES
)
alles = 0
for terugkeertijd, duur, seizoen, regime in rooster:
    alles += 1
    inzet, _, _ = pakket(
        bui(
            return_period=terugkeertijd,
            length_event_hrs=duur,
            time_of_year=seizoen,
            rainfall_regime=regime,
        )
    )
    if not inzet:
        continue
    met_maatregel += 1
    for naam in inzet:
        telling[naam] += 1

print(f"\n{alles} bedreigingen, {met_maatregel} waarbij een maatregel nodig is\n")
for naam, aantal in telling.most_common():
    deel = 100 * aantal / met_maatregel
    print(
        f"  {naam:12s} in {aantal:4d} van de {met_maatregel} pakketten  ({deel:.0f} %)"
    )
