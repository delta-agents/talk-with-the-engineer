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
from talk_with_the_engineer.core.stats.drought import (
    available_regions,
    cumulative_deficit_mm,
)
from talk_with_the_engineer.core.stats.rainfall import (
    _rainfall_for_storm,
)

X0, X1 = 96, 520
# Drie kaders: de natte figuur laat onder zich ruimte voor de trekking, en de
# droge figuur draagt vraag EN aanbod gestapeld - twee grootheden met twee
# eenheden horen niet op een as.
KADERS = {
    "nat": (44, 215),
    "vraag": (40, 158),
    "aanbod": (186, 296),
}


def as_x(t, tmin, tmax):
    return X0 + (X1 - X0) * (np.log10(t) - np.log10(tmin)) / (
        np.log10(tmax) - np.log10(tmin)
    )


def as_y(v, vmax, kader):
    y0, y1 = KADERS[kader]
    return y1 - (y1 - y0) * min(max(v, 0) / vmax, 1.0)


def pad(punten):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in punten)


# ── nat ────────────────────────────────────────────────────────────────────
T_NAT = [0.5, 1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000]
NAT_MAX = 150.0
print(f"// NAT: x T=0,5..1000 (log), y 0..{NAT_MAX:.0f} mm, kader {KADERS['nat']}")
for t in (0.5, 10, 1000):
    print(f"//   T={t:<6g} op x={as_x(t, 0.5, 1000):.1f}")
for duur in (48.0, 96.0, 192.0):
    som = [
        _rainfall_for_storm(float(t), "summer", duur, "R", "p1c", True, None)[1]
        for t in T_NAT
    ]
    punten = [(as_x(t, 0.5, 1000), as_y(v, NAT_MAX, "nat")) for t, v in zip(T_NAT, som)]
    print(
        f"\n// {duur:.0f} uur: {som[0]:.0f} mm bij T=0,5 tot {som[-1]:.0f} mm bij T=1000"
    )
    print(f"//   eindpunt {punten[-1][0]:.1f} {punten[-1][1]:.1f}")
    print(f'u{duur:.0f}: "{pad(punten)}",')

# ── droog ──────────────────────────────────────────────────────────────────
T_DROOG = [2, 5, 10, 25, 50, 100]
DROOG_MAX = 600.0
REGIO = "Aa_en_Maas"
print(f"\n\n// DROOG vraag: y 0..{DROOG_MAX:.0f} mm, kader {KADERS['vraag']}")
for t in (2, 10, 100):
    print(f"//   T={t:<4d} op x={as_x(t, 2, 100):.1f}")

for scenario in ("Referentie", "Hd_2100"):
    mm = [cumulative_deficit_mm(REGIO, scenario, t) for t in T_DROOG]
    punten = [
        (as_x(t, 2, 100), as_y(v, DROOG_MAX, "vraag")) for t, v in zip(T_DROOG, mm)
    ]
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
heen = [(as_x(t, 2, 100), as_y(v, DROOG_MAX, "vraag")) for t, v in zip(T_DROOG, laag)]
terug = [(as_x(t, 2, 100), as_y(v, DROOG_MAX, "vraag")) for t, v in zip(T_DROOG, hoog)][
    ::-1
]
print(
    f"\n// band over 21 waterschappen, Referentie: T=10 van {laag[2]:.0f} tot {hoog[2]:.0f} mm"
)
print(f'band: "{pad(heen + terug)} Z",')

# ── het AANBOD: de rivier ───────────────────────────────────────────────────
# De droogtestatistiek heeft TWEE indicatoren, en de tweede stond niet op het
# scherm: de minimale 7-daagse rivierafvoer als fractie van een normaal jaar.
# Vraag en aanbod op dezelfde herhaaltijd-as.
from talk_with_the_engineer.core.stats.drought import (  # noqa: E402
    normal_year_discharge_m3_per_sec,
    source_availability,
)

print(f"\n\n// AANBOD: fractie 0,5..1,0, kader {KADERS['aanbod']}")
for rivier in ("Rijn", "Maas"):
    fr = [source_availability(REGIO, "Referentie", t, rivier).fraction for t in T_DROOG]
    y0, y1 = KADERS["aanbod"]
    punten = [
        (as_x(t, 2, 100), y1 - (y1 - y0) * (f - 0.5) / 0.5) for t, f in zip(T_DROOG, fr)
    ]
    q = normal_year_discharge_m3_per_sec(rivier)
    print(
        f"\n// {rivier}: normaal jaar {q:.0f} m3/s, T=2 {fr[0]:.3f} tot T=100 {fr[-1]:.3f}"
    )
    print(f"//   eindpunt {punten[-1][0]:.1f} {punten[-1][1]:.1f}")
    print(f'{rivier.lower()}: "{pad(punten)}",')

# ── de TREKKING: een bui is geen getal maar een reeks ──────────────────────
from talk_with_the_engineer.core.stats.rainfall import (  # noqa: E402
    _rainfall_for_storm as _bui,
)

per_dag, som = _bui(10.0, "summer", 96.0, "R", "p1c", True, None)
print(f"\n\n// TREKKING zomer T=10 96 uur: {som:.0f} mm over {len(per_dag)} dagen")
print("//   per dag: " + ", ".join(f"{v:.1f}" for v in per_dag))
print("// wat seizoen en regime met diezelfde bui doen:")
for seizoen in ("summer", "winter"):
    for regime in ("LL", "R", "H"):
        _, v = _bui(10.0, seizoen, 96.0, regime, "p1c", True, None)
        print(f"//   {seizoen:7s} {regime:2s}: {v:5.1f} mm")
