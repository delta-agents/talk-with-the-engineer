"""Genereert de responsecurven van de geprijsde maatregelen: piek tegen euro's.

Eén as voor alle drie, en die as is GELD. Dat is de eerlijke vergelijker: welke
maatregel koopt de meeste centimeter per euro. Normaliseren op "deel van wat
maximaal kan" zou afvoeren plat maken, want zijn bovengrens is twintig keer het
gemaal en dat is geen ambitie maar een zoekgrens.

Uitvoer: SVG-padjes voor de figuur `maatregelcurves` in teken/curven.js.
"""

import sys

sys.path.insert(0, "src")
import numpy as np
from talk_with_the_engineer.core.actions import (
    AfvoerenAction,
    BergenAction,
    VasthoudenAction,
)
from talk_with_the_engineer.core.connection import (
    single_pump_connection,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.transition import simulate

NORM_CM = 30.0
GELD_MAX = 3.0e6  # de x-as loopt tot drie miljoen; daarboven is alles vlak
PIEK_MAX = 40.0
# Het vlak in de viewBox. X1 op 520 en niet op 600: rechts van de curve-einden
# moet ruimte zijn voor de labels, want een label OP een lijn is onleesbaar.
X0, X1, Y0, Y1 = 96, 520, 44, 250


class Bui:
    return_period = 10.0
    time_of_year = "summer"
    length_event_hrs = 192.0
    rainfall_regime = "R"
    name_rainfall_pattern = "p1c"
    days_to_discharge = 2


s0 = PolderState(
    area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
)
basis = simulate(s0, Bui()).dh_max_m * 100


def scherm(euro, piek):
    x = X0 + (X1 - X0) * min(euro / GELD_MAX, 1.0)
    y = Y1 - (Y1 - Y0) * min(max(piek, 0) / PIEK_MAX, 1.0)
    return x, y


def per_eenheid(actie):
    """Wat één eenheid van deze maatregel kost.

    De drie geprijsde maatregelen zijn lineair in hun eigen eenheid - hectare
    open water, hectare land, kubieke meter per seconde - dus dit is exact en
    geen benadering. Daarmee kan de curve in GELDruimte bemonsterd worden.
    """
    boven = actie.upper_bound(s0)
    proef = boven / 100.0
    return actie.at(proef).cost(s0) / proef


def curve(actie, punten=60):
    """(pad, alle punten, het optimum) voor een maatregel.

    Bemonsterd langs de GELDas en niet langs de maatvoering: één hectare bergen
    kost 135 duizend euro, dus een raster over de maatvoering geeft twee punten
    op drie miljoen en een raster over het geld geeft er zestig.
    """
    stap = per_eenheid(actie)
    boven = actie.upper_bound(s0)
    xy, ruw = [], []
    for euro in np.linspace(0, min(GELD_MAX, boven * stap), punten):
        x = euro / stap
        piek = simulate(actie.at(float(x)).apply(s0), Bui()).dh_max_m * 100
        ruw.append((euro, piek, float(x)))
        xy.append(scherm(euro, piek))
    pad = "M" + " L".join(f"{q[0]:.1f} {q[1]:.1f}" for q in xy)
    return pad, ruw, min(ruw, key=lambda r: r[1])


print(f"// basispiek {basis:.1f} cm, norm {NORM_CM:.0f} cm")
print(f"// x-as 0..{GELD_MAX / 1e6:.0f} mln euro, y-as 0..{PIEK_MAX:.0f} cm")
print(f"// norm op y={Y1 - (Y1 - Y0) * NORM_CM / PIEK_MAX:.1f}")
for naam, actie in (
    ("vasthouden", VasthoudenAction()),
    ("bergen", BergenAction()),
    ("afvoeren", AfvoerenAction()),
):
    pad, ruw, best = curve(actie)
    bx, by = scherm(best[0], best[1])
    print(
        f"\n// {naam}: laagste piek {best[1]:.1f} cm bij {best[0] / 1e6:.2f} mln"
        f" ({best[2]:.3g} eenheden)"
    )
    print(f"//   optimum op scherm: {bx:.1f} {by:.1f}")
    print(f'{naam}: "{pad}",')
