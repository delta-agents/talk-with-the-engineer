"""Genereert de responsecurve van bergen, en de twee lezingen ervan.

Dit is de plaat bij `T`. Eén kromme - hoeveel hectare open water tegen hoe hoog
de piek komt - en twee manieren om hem te lezen:

* HEEN  geef de maatregel, lees de stand. Dat is `simulate`.
* TERUG geef de stand die je wilt, lees de maatregel. Dat is `solve`, en die is
        exact: bisectie op een monotone tak, geen zoektocht in het duister.

De twee getallenvoorbeelden komen uit diezelfde twee functies, zodat wat op het
scherm staat te reproduceren is met twee regels code.

Uitvoer gaat naar stdout en hoort in `transitiePaneel` in teken/schema.js.
"""

import sys

sys.path.insert(0, "src")
import numpy as np

from talk_with_the_engineer.core.actions import BergenAction
from talk_with_the_engineer.core.connection import (
    single_pump_connection,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.transition import simulate
from talk_with_the_engineer.core.inverse import solve

# Het kader van het onderste paneel in `transitiePaneel`. X0 en X1 zijn zo
# gekozen dat de plot op het scherm precies onder die van de statistiekplaat bij
# `E` valt: die staat op 96..520 in een viewBox van 660, deze op 85..592 in een
# viewBox van -30..760, en beide worden op hun breedte uitgetekend.
X0, X1, Y0, Y1 = 85.0, 592.0, 268.0, 408.0
HA_MAX = 80.0  # hectare open water erbij, over de volle breedte
PIEK_MAX = 40.0  # centimeter, over de volle hoogte

HEEN_HA = 40.0  # het voorbeeld heen: deze maatregel, welke stand?
TERUG_CM = 30.0  # het voorbeeld terug: de inundatienorm, welke maatregel?


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
basis_cm = simulate(s0, Bui()).dh_max_m * 100


def scherm(ha, piek_cm):
    return (
        X0 + (X1 - X0) * min(ha / HA_MAX, 1.0),
        Y1 - (Y1 - Y0) * min(max(piek_cm, 0.0) / PIEK_MAX, 1.0),
    )


def piek_bij(ha):
    return simulate(BergenAction().at(float(ha)).apply(s0), Bui()).dh_max_m * 100


punten = [(ha, piek_bij(ha)) for ha in np.linspace(0, HA_MAX, 41)]
pad = "M" + " L".join(f"{scherm(*p)[0]:.1f} {scherm(*p)[1]:.1f}" for p in punten)

heen_cm = piek_bij(HEEN_HA)
antwoord = solve(s0, Bui(), BergenAction(), TERUG_CM / 100.0)
terug_ha = antwoord.magnitude

print(
    f"// kale piek {basis_cm:.1f} cm; x-as 0..{HA_MAX:.0f} ha, y-as 0..{PIEK_MAX:.0f} cm"
)
print(f'// de kromme: "{pad}"')
print()
kaal_y = scherm(0, basis_cm)[1]
print(f"// de kale piek staat op y {kaal_y:.1f}")
print()
print(
    f"// HEEN: {HEEN_HA:.0f} ha bergen -> piek {heen_cm:.1f} cm, "
    f"dus {basis_cm - heen_cm:.0f} cm lager"
)
hx, hy = scherm(HEEN_HA, heen_cm)
print(f"//   knik op {hx:.1f} {hy:.1f}; van de x-as omhoog en naar de y-as links")
print(f'//   "M{hx:.1f} {Y1:.1f} L{hx:.1f} {hy:.1f} L{X0:.1f} {hy:.1f}"')
print(f"//   de verlaging loopt van y {kaal_y:.1f} tot y {hy:.1f}")
print()
print(
    f"// TERUG: piek onder {TERUG_CM:.0f} cm -> {terug_ha:.1f} ha bergen "
    f"({antwoord.status.value}, {antwoord.unit}), dus "
    f"{basis_cm - TERUG_CM:.0f} cm lager"
)
tx, ty = scherm(terug_ha, TERUG_CM)
print(f"//   knik op {tx:.1f} {ty:.1f}; van de y-as naar rechts en omlaag naar de x-as")
print(f'//   "M{X0:.1f} {ty:.1f} L{tx:.1f} {ty:.1f} L{tx:.1f} {Y1:.1f}"')
print(f"//   de verlaging loopt van y {kaal_y:.1f} tot y {ty:.1f}")
