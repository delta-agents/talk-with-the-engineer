"""Genereert de oplossingsruimte van vasthouden en afvoeren bij één eis: de piek onder 18 cm.

Print het raster (elke combinatie doorgerekend), de rand (per gemaalmaat de hectares
vasthouden die de eis precies halen, uit de inverse vraag) en het goedkoopste pakket.
"""

import sys

sys.path.insert(0, "src")

import numpy as np

from talk_with_the_engineer.core.actions import DischargeAction, RetentionAction
from talk_with_the_engineer.core.inverse import solve
from talk_with_the_engineer.core.package import Constraints
from talk_with_the_engineer.core.preference import measures_in_the_cheapest_package
from talk_with_the_engineer.core.reference import REFERENCE_POLDER, REFERENCE_STORM
from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.core.transition import simulate

EIS_M = 0.18
POMP, HA = (0.0, 0.6), (0.0, 750.0)
# Plotvlak in SVG-coördinaten: x is afvoeren, y is vasthouden (omhoog).
X, Y = (110.0, 560.0), (300.0, 40.0)

vasthouden, afvoeren = RetentionAction(), DischargeAction()


def svg(pomp, ha):
    return f"{np.interp(pomp, POMP, X):.1f} {np.interp(ha, HA, Y):.1f}"


def met_gemaal(pomp):
    return afvoeren.at(float(pomp)).apply(REFERENCE_POLDER)


def haalt(pomp, ha):
    polder = vasthouden.at(float(ha)).apply(met_gemaal(pomp))
    return simulate(polder, REFERENCE_STORM).dh_max_m <= EIS_M + 1e-9


def rand_bij(pomp):
    """De hectares vasthouden die bij dit gemaal de eis precies halen, of None."""
    if haalt(pomp, 0.0):
        return 0.0
    uitkomst = solve(met_gemaal(pomp), REFERENCE_STORM, vasthouden, EIS_M)
    return uitkomst.magnitude if uitkomst.status is SolveStatus.EXACT else None


def kosten(punt):
    pomp, ha = punt
    return sum(
        actie.at(float(maat)).cost(REFERENCE_POLDER)
        for actie, maat in ((afvoeren, pomp), (vasthouden, ha))
    )


raster = [
    (pomp, ha, haalt(pomp, ha))
    for ha in np.linspace(*HA, 11)
    for pomp in np.linspace(*POMP, 13)
]
print("# het raster: x y haalt")
for pomp, ha, ok in raster:
    print(f"[{svg(pomp, ha)}, {int(ok)}]")
print(f"# {len(raster)} doorrekeningen, {sum(ok for *_, ok in raster)} halen de eis")

pakket = measures_in_the_cheapest_package(
    REFERENCE_POLDER, REFERENCE_STORM, Constraints(max_dh_total_m=EIS_M)
)
print(f"\n# het goedkoopste pakket: {pakket}")

# Het pakket gaat als eigen punt de rand in, zodat de rand door de knik loopt.
maten = sorted({*np.linspace(*POMP, 25).round(4), round(pakket["afvoeren"], 4)})
rand = [(pomp, ha) for pomp in maten if (ha := rand_bij(pomp)) is not None]
print("\n# de rand: pomp ha kosten")
for punt in rand:
    print(f"# {punt[0]:.3f} m3/s {punt[1]:6.1f} ha  EUR {kosten(punt) / 1e6:.2f} mln")
print("M" + " L".join(svg(*punt) for punt in rand))

knik = min(rand, key=kosten)
print(f"\n# de knik: {knik[1]:.0f} ha + {knik[0]:.2f} m3/s -> ({svg(*knik)})")
