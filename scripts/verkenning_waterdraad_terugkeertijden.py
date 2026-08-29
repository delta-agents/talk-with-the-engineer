"""De waterdraad over de terugkeertijden: drie pakketten, nat en droog per T.

Nat: per pakket en per T (2..100) een simulate_network-run; per knoop de piek, per rand
de uren op capaciteit. Droog: per pakket, gebied en T het onvervulde tekort uit
simulate_deficit (per gebied afzonderlijk, zonder verdeling over een gedeelde bron - de
allocate-laag blijft hier bewust buiten beeld en dat hoort de pagina te melden).
"""

import json

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AfvoerenAction,
    BergenAction,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.system import SystemState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.network import simulate_network
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    simulate_deficit,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.supply import Deficit
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
    cumulative_deficit_mm,
)

BASE = {
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
    "rainfall_regime": "R",
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}
TS = [2, 5, 10, 25, 50, 100]
REGION, SCENARIO, SEASON_DAYS = "Delfland", "Referentie", 183

names = ["Hooghout", "Leegveld", "Middelblok", "Zuidplas", "Randwijk", "Boezem"]
areas = [1500.0, 2500.0, 4000.0, 3000.0, 2000.0, 6000.0]
pcts = [2.5, 3.5, 3.0, 4.5, 3.5, 8.0]
caps = [3.0, 5.0, 6.0, 11.0, 13.0, 30.0]
n, H = len(names), 168

# de droge kant heeft een peilband en een inlaat nodig, anders is het tekort overal
# exact het neerslagtekort en zegt de kolom niets; inlaat in m3/s, ~0,25-0,5 l/s/ha
INLETS = [0.20, 0.38, 0.65, 0.48, 0.28, 1.00]
MARGIN_M = 0.25


def fresh_polders():
    return [
        PolderState(
            area_ha=areas[i],
            pct_open_water=pcts[i],
            level_margin_m=MARGIN_M,
            connections=(
                Connection(
                    to=OUTSIDE if i == n - 1 else names[i + 1],
                    capacity_out_m3_per_sec=caps[i],
                    capacity_in_m3_per_sec=INLETS[i],
                ),
            ),
        )
        for i in range(n)
    ]


def applied(steps):
    polders = fresh_polders()
    for node_name, action in steps:
        idx = names.index(node_name)
        polders[idx] = action.apply(polders[idx])
    return polders


PACKAGES = [
    ("referentie", "geen maatregelen", []),
    (
        "geconcentreerd",
        "alle drie de maatregelen op Middelblok",
        [
            ("Middelblok", VasthoudenAction(delta_retention_ha=1000)),
            ("Middelblok", BergenAction(delta_open_water_ha=100)),
            ("Middelblok", AfvoerenAction(delta_pump_capacity_m3_per_sec=4)),
        ],
    ),
    (
        "gespreid",
        "vasthouden op Leegveld, bergen op Middelblok, afvoeren op Randwijk",
        [
            ("Leegveld", VasthoudenAction(delta_retention_ha=1000)),
            ("Middelblok", BergenAction(delta_open_water_ha=100)),
            ("Randwijk", AfvoerenAction(delta_pump_capacity_m3_per_sec=4)),
        ],
    ),
]

packages = []
for name, sub, steps in PACKAGES:
    polders = applied(steps)
    system = SystemState.from_polders(list(polders), names=names)
    wet_peaks = {i: {} for i in range(n)}
    edge_full = {i: {} for i in range(n)}
    for T in TS:
        storm = StoreInputGivenH(**BASE, return_period=T, delta_h_available=1.0)
        r = simulate_network(system, storm)
        for i in range(n):
            wet_peaks[i][T] = round(float(r.water_level_m[i, :H].max()), 3)
            u = r.exchange_m3_per_sec[i, :H] / caps[i]
            edge_full[i][T] = int((u > 0.999).sum())
    dry = {i: {} for i in range(n)}
    for T in TS:
        cum = cumulative_deficit_mm(REGION, SCENARIO, T)
        deficit = Deficit(cum / SEASON_DAYS, SEASON_DAYS)
        for i in range(n):
            res = simulate_deficit(polders[i], deficit)
            dry[i][T] = round(float(res.shortfall_mm), 1)
    packages.append(
        {
            "name": name,
            "sub": sub,
            "grip": [(type(a).name_nl, node) for node, a in steps],
            "nodes": [
                {
                    "name": names[i],
                    "wet": [wet_peaks[i][T] for T in TS],
                    "dry": [dry[i][T] for T in TS],
                }
                for i in range(n)
            ],
            "edges": [
                {
                    "to": "buitenwater" if i == n - 1 else names[i + 1],
                    "capacity": caps[i],
                    "hours_full": [edge_full[i][T] for T in TS],
                }
                for i in range(n)
            ],
        }
    )

print(
    json.dumps(
        {
            "meta": {
                "Ts": TS,
                "storm_vorm": "winter, 96 u, p1a",
                "hours": H,
                "drought": REGION
                + " · "
                + SCENARIO
                + " · groeiseizoen 183 d, peilmarge 0,25 m, eigen inlaat per gebied, zonder verdeling over een gedeelde bron",
                "bron": "18 simulate_network-runs (nat) en 108 simulate_deficit-runs (droog)",
            },
            "packages": packages,
        }
    )
)
