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

Uitvoer gaat naar stdout en hoort in `topdownNatDroog` in presentatie.js, tussen
de GEGENEREERD-bakens.
"""

import sys

sys.path.insert(0, "src")
import numpy as np

from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    OUTSIDE,
    Connection,
    single_pump_connection,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    NO_SOIL,
    simulate,
    simulate_deficit,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
    cumulative_deficit_mm,
)

# Het kader deelt zijn breedte met de tijdbalk eronder; zie `topdownNatDroog`.
X0, X1 = 570.0, 830.0
NAT_TOP, NAT_BOD = 30.0, 150.0
DROOG_TOP, DROOG_BOD = 282.0, 402.0
SCHEIDING = 0.44  # waar in het natte kader de neerslag ophoudt en de afvoer begint

REGEN_AS = 32.0  # mm/dag op de volle hoogte van de neerslagband
AFVOER_AS = 3.5  # l/s/ha op de volle hoogte van de afvoerband
TEKORT_AS = 300.0  # mm over de volle hoogte van het droge kader

SEIZOEN_DAGEN = 183
REGIO, SCENARIO, HERHAALTIJD = "Aa_en_Maas", "Referentie", 10


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
r = simulate(state, Bui())

afvoer = np.asarray(r.drainage_l_s_ha)
regen = np.asarray(r.rainfall_per_day_mm)
dagen = len(afvoer) / 24.0
# De capaciteit van het gemaal in dezelfde eenheid als de afvoercurve: die telt
# per hectare LAND, want dat is het oppervlak dat afvoert.
plafond = state.pump_capacity_m3_per_sec * 1000.0 / state.area_land_ha

NAT_SPLIT = NAT_TOP + SCHEIDING * (NAT_BOD - NAT_TOP)


def nat_x(dag):
    return X0 + (X1 - X0) * dag / dagen


def regen_y(mm):
    return NAT_TOP + (NAT_SPLIT - NAT_TOP) * min(mm / REGEN_AS, 1.0)


def afvoer_y(l_s_ha):
    return NAT_BOD - (NAT_BOD - NAT_SPLIT - 8) * min(l_s_ha / AFVOER_AS, 1.0)


print(f"// ── nat: {len(regen):.0f} dagen bui, T=10, zomer, regime R")
print(f"// neerslag tot {regen.max():.1f} mm/dag, as tot {REGEN_AS:.0f}")
print(f"// afvoer tot {afvoer.max():.2f} l/s/ha, as tot {AFVOER_AS:.1f}")
print(
    f"// gemaal {state.pump_capacity_m3_per_sec} m3/s over "
    f"{state.area_land_ha:.0f} ha land = {plafond:.2f} l/s/ha"
)
print()

print("// de staafjes van de neerslag, van de bovenrand af")
staven = []
for i, mm in enumerate(regen):
    if mm <= 0:
        continue
    breed = (X1 - X0) / dagen
    x = nat_x(i) + breed * 0.16
    staven.append(f'["{x:.1f}", "{breed * 0.68:.1f}", "{regen_y(mm) - NAT_TOP:.1f}"]')
print("[" + ", ".join(staven) + "]")
print()

# De afvoerreeks is per DAG en staat per uur herhaald in de uitkomst. De GETALLEN
# zijn dus die dagwaarden; de curve ertussen is interpolatie, en die is monotoon
# (Fritsch-Carlson) zodat er nergens een piek of een dal bij wordt verzonnen dat
# in de reeks niet zit. Een hydrograaf hoort vloeiend te lopen, en een trapje van
# negen treden leest als een staafgrafiek van iets anders.
dag_afvoer = afvoer[::24]


def monotone_hellingen(xs, ys):
    """Fritsch-Carlson: raaklijnen die geen over- of onderschot geven."""
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [(d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        t = a * a + b * b
        if t > 9:
            k = 3.0 / t**0.5
            m[i], m[i + 1] = k * a * d[i], k * b * d[i]
    return m


# De dagwaarde hoort in het MIDDEN van zijn dag; de ankers op dag 0 en dag 9
# hangen de curve aan de nullijn en aan de staart die nog loopt als het venster
# dichtgaat.
xs = [0.0] + [i + 0.5 for i in range(len(dag_afvoer))] + [float(len(dag_afvoer))]
ys = [0.0] + [float(v) for v in dag_afvoer] + [float(dag_afvoer[-1])]
m = monotone_hellingen(xs, ys)

pad = f"M{nat_x(xs[0]):.1f} {afvoer_y(ys[0]):.1f}"
for i in range(len(xs) - 1):
    h = xs[i + 1] - xs[i]
    c1 = (xs[i] + h / 3, ys[i] + m[i] * h / 3)
    c2 = (xs[i + 1] - h / 3, ys[i + 1] - m[i + 1] * h / 3)
    pad += (
        f" C{nat_x(c1[0]):.1f} {afvoer_y(c1[1]):.1f}"
        f" {nat_x(c2[0]):.1f} {afvoer_y(c2[1]):.1f}"
        f" {nat_x(xs[i + 1]):.1f} {afvoer_y(ys[i + 1]):.1f}"
    )

print("// de afvoercurve, monotoon door de dagwaarden")
print(f'"{pad}"')
# Het vlak is dezelfde curve, dichtgetrokken op de nullijn. Zo hoeft de tekening
# de curve niet twee keer te dragen met een kans dat ze uit elkaar lopen.
print(
    f'// als vlak: dezelfde curve + " L{X1:.1f} {NAT_BOD:.1f} L{X0:.1f} {NAT_BOD:.1f} Z"'
)
print("// per dag [l/s/ha]: " + ", ".join(f"{v:.2f}" for v in dag_afvoer))
print(f"// plafond op y {afvoer_y(plafond):.1f}")
print(
    f"// piek van de afvoer op dag {afvoer.argmax() / 24.0:.2f}, "
    f"de bui op dag {regen.argmax() + 0.5:.2f}"
)
print()

# ── droog ──────────────────────────────────────────────────────────────────
tekort_mm = cumulative_deficit_mm(REGIO, SCENARIO, HERHAALTIJD)
per_dag = tekort_mm / SEIZOEN_DAGEN


class Tekort:
    deficit_mm_per_day = per_dag
    length_days = SEIZOEN_DAGEN


droog = PolderState(
    area_ha=1000,
    pct_open_water=5.0,
    connections=(
        Connection(to=OUTSIDE, capacity_out_m3_per_sec=1.5, capacity_in_m3_per_sec=0.0),
    ),
    target_level_rise_m=0.20,
    level_margin_m=0.10,
)
d = simulate_deficit(droog, Tekort(), NO_SOIL)


def droog_x(dag):
    return X0 + (X1 - X0) * dag / SEIZOEN_DAGEN


def droog_y(mm):
    return DROOG_TOP + (DROOG_BOD - DROOG_TOP) * min(mm / TEKORT_AS, 1.0)


leeg = d.days_until_buffer_empty
print(
    f"// ── droog: {tekort_mm:.0f} mm over {SEIZOEN_DAGEN} dagen "
    f"({REGIO}, {SCENARIO}, T={HERHAALTIJD})"
)
print(
    f"// eigen voorraad {d.buffer_mm:.0f} mm, op na {leeg:.1f} dagen; "
    f"tekort dat blijft {d.shortfall_mm:.0f} mm"
)
print(
    f'// de vraag: "M{droog_x(0):.1f} {droog_y(0):.1f} '
    f'L{droog_x(SEIZOEN_DAGEN):.1f} {droog_y(tekort_mm):.1f}"'
)
print(
    f'// de eigen voorraad: "M{droog_x(0):.1f} {droog_y(0):.1f} '
    f"L{droog_x(leeg):.1f} {droog_y(d.buffer_mm):.1f} "
    f'L{droog_x(SEIZOEN_DAGEN):.1f} {droog_y(d.buffer_mm):.1f}"'
)
print(f"// as tot {TEKORT_AS:.0f} mm")
