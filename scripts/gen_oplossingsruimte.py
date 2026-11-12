"""Genereert de oplossingsruimte van vasthouden en afvoeren bij één eis: de piek onder 18 cm.

Print de piek op elk rasterpunt, de rand waar de eis precies gehaald wordt, twee routes die
de maatregelen in een andere volgorde nemen, en het goedkoopste pakket.
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
POMPEN, HECTARES = np.linspace(0.0, 0.6, 13), np.linspace(0.0, 750.0, 11)
# De eerste stap van elke route: wat er op voorhand vastligt.
EERST_VASTHOUDEN_HA, EERST_GEMAAL_M3S = 225.0, 0.2

vasthouden, afvoeren = RetentionAction(), DischargeAction()


def polder(pomp, ha):
    return vasthouden.at(float(ha)).apply(
        afvoeren.at(float(pomp)).apply(REFERENCE_POLDER)
    )


def piek_cm(pomp, ha):
    return simulate(polder(pomp, ha), REFERENCE_STORM).dh_max_m * 100


def rest(actie, pomp, ha):
    """Hoeveel van `actie` de eis nog vraagt bovenop dit gemaal en deze hectares, of None."""
    if piek_cm(pomp, ha) <= EIS_M * 100:
        return 0.0
    uitkomst = solve(polder(pomp, ha), REFERENCE_STORM, actie, EIS_M)
    return uitkomst.magnitude if uitkomst.status is SolveStatus.EXACT else None


def kosten(punt):
    return sum(
        actie.at(float(maat)).cost(REFERENCE_POLDER)
        for actie, maat in zip((afvoeren, vasthouden), punt)
    )


print("# de piek in cm: een rij per maat vasthouden, een kolom per gemaalmaat")
for ha in HECTARES:
    print("[" + ", ".join(f"{piek_cm(pomp, ha):.1f}" for pomp in POMPEN) + "],")

pakket = measures_in_the_cheapest_package(
    REFERENCE_POLDER, REFERENCE_STORM, Constraints(max_dh_total_m=EIS_M)
)
print(f"\n# het goedkoopste pakket: {pakket}")

# Het pakket gaat als eigen punt de rand in, zodat de rand door de knik loopt.
maten = sorted({*np.linspace(0.0, 0.6, 25).round(4), round(pakket["afvoeren"], 4)})
rand = [(pomp, ha) for pomp in maten if (ha := rest(vasthouden, pomp, 0.0)) is not None]
print("\n# de rand: gemaal in m3/s, vasthouden in ha, kosten in mln")
for punt in rand:
    print(f"[{punt[0]:.4f}, {punt[1]:.1f}],  // EUR {kosten(punt) / 1e6:.2f} mln")

print("\n# route A: eerst vasthouden, dan het gemaal voor de rest")
print(
    f"# {EERST_VASTHOUDEN_HA:.0f} ha geeft {piek_cm(0.0, EERST_VASTHOUDEN_HA):.1f} cm; "
    f"de rest vraagt {rest(afvoeren, 0.0, EERST_VASTHOUDEN_HA):.3f} m3/s"
)
print("# route B: eerst het gemaal, dan vasthouden voor de rest")
print(
    f"# {EERST_GEMAAL_M3S} m3/s geeft {piek_cm(EERST_GEMAAL_M3S, 0.0):.1f} cm; "
    f"de rest vraagt {rest(vasthouden, EERST_GEMAAL_M3S, 0.0):.1f} ha"
)
