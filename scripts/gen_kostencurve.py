"""Genereert de kostencurve: wat het goedkoopste pakket kost per beschermingseis.

Dit is de vorm die de literatuur gebruikt. Van Dantzig (1956) en Eijgenraam
zetten de INVESTERINGSKOSTEN tegen het veiligheidsniveau en tellen daar de
resterende verwachte schade bij op; het optimum ligt waar die som minimaal is.

Wij kunnen alleen de eerste helft tekenen. De vermeden jaarschade hebben we
niet, dus de curve die je erbij nodig hebt om een optimum te vinden ontbreekt -
en dat is precies wat deze figuur zichtbaar moet maken.
"""

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

X0, X1, Y0, Y1 = 96, 520, 44, 250
NORM_LINKS, NORM_RECHTS = 36.0, 10.0  # links de kale piek, rechts de ambitie
KOSTEN_MAX = 2.0e6


class Bui:
    return_period = 10.0
    time_of_year = "summer"
    length_event_hrs = 192.0
    rainfall_regime = "R"
    name_rainfall_pattern = "p1c"
    days_to_discharge = 2


state = PolderState(
    area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
)

NORMEN = [36, 34, 32, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10]


def scherm(norm_cm, euro):
    x = X0 + (X1 - X0) * (NORM_LINKS - norm_cm) / (NORM_LINKS - NORM_RECHTS)
    y = Y1 - (Y1 - Y0) * min(euro / KOSTEN_MAX, 1.0)
    return x, y


punten = []
print(f"// x: norm {NORM_LINKS:.0f} cm links tot {NORM_RECHTS:.0f} cm rechts")
print(f"// y: 0 tot {KOSTEN_MAX / 1e6:.0f} mln euro")
for cm in NORMEN:
    p = optimize(state, Bui(), Constraints(max_dh_total_m=cm / 100)).best
    punten.append(scherm(cm, p.cost))
    inzet = (
        ", ".join(f"{k} {v:.3g}" for k, v in p.quantities.items() if v > 1e-9)
        or "niets"
    )
    print(f"//   norm {cm:2d} cm: {p.cost / 1e6:5.3f} mln  ({inzet})")

for cm in (30, 20):
    x, y = scherm(
        cm, optimize(state, Bui(), Constraints(max_dh_total_m=cm / 100)).best.cost
    )
    print(f"// merkpunt norm {cm} cm op {x:.1f} {y:.1f}")

print()
print('kosten: "M' + " L".join(f"{x:.1f} {y:.1f}" for x, y in punten) + '",')
