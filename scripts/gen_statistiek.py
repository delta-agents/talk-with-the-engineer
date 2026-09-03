"""Genereert de twee statistiekfiguren van stap E: nat en droog.

Twee vormen, en het verschil ertussen is het punt van de stap:

* NAT   de neerslagstatistiek varieert de GEBEURTENIS - dezelfde zomer, drie
        buiduren, van eens per half jaar tot eens per duizend jaar. STOWA 2019.
* DROOG de droogtestatistiek varieert het KLIMAAT - hetzelfde groeiseizoen,
        zeven KNMI'23-scenario's, plus de spreiding over de eenentwintig
        waterschappen als band. STOWA 2025-23.

Uitvoer: SVG-padjes voor `neerslagstatistiek` en `droogtestatistiek`.
"""

import sys

sys.path.insert(0, "src")
import numpy as np
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
    available_regions,
    cumulative_deficit_mm,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    _rainfall_for_storm,
)

X0, X1, Y0, Y1 = 96, 520, 44, 250


def as_x(t, tmin, tmax):
    return X0 + (X1 - X0) * (np.log10(t) - np.log10(tmin)) / (
        np.log10(tmax) - np.log10(tmin)
    )


def as_y(v, vmax):
    return Y1 - (Y1 - Y0) * min(max(v, 0) / vmax, 1.0)


def pad(punten):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in punten)


# ── nat ────────────────────────────────────────────────────────────────────
T_NAT = [0.5, 1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000]
NAT_MAX = 150.0
print(f"// NAT: x T=0,5..1000 (log), y 0..{NAT_MAX:.0f} mm")
for t in (0.5, 10, 1000):
    print(f"//   T={t:<6g} op x={as_x(t, 0.5, 1000):.1f}")
for duur in (48.0, 96.0, 192.0):
    som = [
        _rainfall_for_storm(float(t), "summer", duur, "R", "p1c", True, None)[1]
        for t in T_NAT
    ]
    punten = [(as_x(t, 0.5, 1000), as_y(v, NAT_MAX)) for t, v in zip(T_NAT, som)]
    print(
        f"\n// {duur:.0f} uur: {som[0]:.0f} mm bij T=0,5 tot {som[-1]:.0f} mm bij T=1000"
    )
    print(f"//   eindpunt {punten[-1][0]:.1f} {punten[-1][1]:.1f}")
    print(f'u{duur:.0f}: "{pad(punten)}",')

# ── droog ──────────────────────────────────────────────────────────────────
T_DROOG = [2, 5, 10, 25, 50, 100]
DROOG_MAX = 600.0
REGIO = "Aa_en_Maas"
print(f"\n\n// DROOG: x T=2..100 (log), y 0..{DROOG_MAX:.0f} mm")
for t in (2, 10, 100):
    print(f"//   T={t:<4d} op x={as_x(t, 2, 100):.1f}")

for scenario in ("Referentie", "Hd_2100"):
    mm = [cumulative_deficit_mm(REGIO, scenario, t) for t in T_DROOG]
    punten = [(as_x(t, 2, 100), as_y(v, DROOG_MAX)) for t, v in zip(T_DROOG, mm)]
    print(f"\n// {scenario}: {mm[0]:.0f} mm bij T=2 tot {mm[-1]:.0f} mm bij T=100")
    print(f"//   eindpunt {punten[-1][0]:.1f} {punten[-1][1]:.1f}")
    print(f'{scenario.lower()}: "{pad(punten)}",')

# De band is de spreiding over de waterschappen bij het huidige klimaat: heen
# langs de laagste en terug langs de hoogste, zodat het één gesloten vlak is.
laag, hoog = [], []
for t in T_DROOG:
    w = [cumulative_deficit_mm(r, "Referentie", t) for r in available_regions()]
    w = [x for x in w if x]
    laag.append(min(w))
    hoog.append(max(w))
heen = [(as_x(t, 2, 100), as_y(v, DROOG_MAX)) for t, v in zip(T_DROOG, laag)]
terug = [(as_x(t, 2, 100), as_y(v, DROOG_MAX)) for t, v in zip(T_DROOG, hoog)][::-1]
print(
    f"\n// band over 21 waterschappen, Referentie: T=10 van {laag[2]:.0f} tot {hoog[2]:.0f} mm"
)
print(f'band: "{pad(heen + terug)} Z",')
