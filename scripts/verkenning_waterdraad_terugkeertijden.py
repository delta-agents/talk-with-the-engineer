"""Ronde 5: de droge kant door de verdringingsreeks — één bron, verdeeld over de boom.

Nat als ronde 4 (simulate_network per T). Droog nieuw: per T gaat de netto vraag (het
cumulatief tekort minus de eigen peilbuffer) van alle gebieden naar `allocate`, dat een
EINDIGE bron over de boom verdeelt, lexicografisch per verdringingscategorie. Een tweede
run met onbeperkte bron splitst elk tekort in een inlaat-deel en een bron-deel — het
onderscheid dat alleen de allocatielaag kan maken. Vereenvoudiging die de pagina meldt:
de buffer gaat er vooraf statisch af; de echte tijdsdynamiek van buffer én verdeling
samen is een kernvraag, geen visualisatievraag.
"""

import json

import numpy as np
from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH
from talk_with_the_engineer.core.actions import (
    DischargeAction,
    RetentionAction,
    StorageAction,
)
from talk_with_the_engineer.core.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.system import SystemState
from talk_with_the_engineer.core.allocation import allocate
from talk_with_the_engineer.core.network import simulate_network
from talk_with_the_engineer.core.stats.drought import (
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
AVAILABLE_M3 = (
    40_000_000.0  # de gedeelde bron over het seizoen; eindig, en dat is het punt
)

names = ["Hooghout", "Leegveld", "Middelblok", "Zuidplas", "Randwijk", "Boezem"]
areas = [1500.0, 2500.0, 4000.0, 3000.0, 2000.0, 6000.0]
pcts = [2.5, 3.5, 3.0, 4.5, 3.5, 8.0]
caps = [3.0, 5.0, 6.0, 11.0, 13.0, 30.0]
INLETS = [0.20, 0.38, 0.65, 0.48, 0.28, 1.00]
# één verdringingscategorie per gebied is een vereenvoudiging (echte vraag is per gebied
# gemengd over de posten); 2 = nutsvoorziening, 3 = kapitaalintensief, 4 = overig
CATEGORIES = [3, 4, 4, 3, 4, 2]
MARGIN_M = 0.25
n, H = len(names), 168


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
            ("Middelblok", RetentionAction(delta_retention_ha=1000)),
            ("Middelblok", StorageAction(delta_open_water_ha=100)),
            ("Middelblok", DischargeAction(delta_pump_capacity_m3_per_sec=4)),
        ],
    ),
    (
        "gespreid",
        "vasthouden op Leegveld, bergen op Middelblok, afvoeren op Randwijk",
        [
            ("Leegveld", RetentionAction(delta_retention_ha=1000)),
            ("Middelblok", StorageAction(delta_open_water_ha=100)),
            ("Randwijk", DischargeAction(delta_pump_capacity_m3_per_sec=4)),
        ],
    ),
]

packages = []
AORTA_M3S = 4.0  # de doorvoercapaciteit van de boezem zelf


def dry_system(polders):
    """De droge boom is niet de natte ketting: aanvoer hangt als ster aan de boezem.

    Afvoer loopt in serie (mijn uitstroom is jouw aanvoer), maar de inlaten trekken elk
    rechtstreeks uit de boezem. Zonder deze omkering moest in de eerste opzet alle vraag
    door de boezem-inlaat van de keten heen en was die ene inlaat de flessenhals voor
    alles - hydrologisch onzin, en de reden dat dit een eigen topologie verdient.
    """
    star = []
    for i, polder in enumerate(polders):
        to = OUTSIDE if names[i] == "Boezem" else "Boezem"
        cap_in = AORTA_M3S if names[i] == "Boezem" else INLETS[i]
        star.append(
            polder.model_copy(
                update={
                    "connections": (
                        Connection(
                            to=to,
                            capacity_out_m3_per_sec=caps[i],
                            capacity_in_m3_per_sec=cap_in,
                        ),
                    )
                }
            )
        )
    return SystemState.from_polders(star, names=names)


for name, sub, steps in PACKAGES:
    polders = applied(steps)
    system = SystemState.from_polders(list(polders), names=names)
    system_dry = dry_system(polders)
    land_m2 = np.array([p.area_land_ha * 1e4 for p in polders])
    buffer_mm = np.array(
        [MARGIN_M * 1000.0 * p.area_open_water_ha / p.area_ha for p in polders]
    )

    wet_peaks = {i: {} for i in range(n)}
    edge_full = {i: {} for i in range(n)}
    for T in TS:
        storm = StoreInputGivenH(**BASE, return_period=T, delta_h_available=1.0)
        r = simulate_network(system, storm)
        for i in range(n):
            wet_peaks[i][T] = round(float(r.water_level_m[i, :H].max()), 3)
            u = r.exchange_m3_per_sec[i, :H] / caps[i]
            edge_full[i][T] = int((u > 0.999).sum())

    dry_total, dry_source, dry_cov, binding_cat, source_used = (
        {i: {} for i in range(n)},
        {i: {} for i in range(n)},
        {i: {} for i in range(n)},
        {},
        {},
    )
    for T in TS:
        cum = cumulative_deficit_mm(REGION, SCENARIO, T)
        demand_mm = np.maximum(0.0, cum - buffer_mm)
        demand_m3 = demand_mm / 1000.0 * land_m2
        real = allocate(
            system_dry, demand_m3, np.array(CATEGORIES), AVAILABLE_M3, SEASON_DAYS
        )
        unlimited = allocate(
            system_dry, demand_m3, np.array(CATEGORIES), float("inf"), SEASON_DAYS
        )
        for i in range(n):
            total_mm = float(real.shortfall_m3[i] / land_m2[i] * 1000.0)
            inlet_mm = float(unlimited.shortfall_m3[i] / land_m2[i] * 1000.0)
            dry_total[i][T] = round(total_mm, 1)
            dry_source[i][T] = round(max(0.0, total_mm - inlet_mm), 1)
            dry_cov[i][T] = round(float(real.coverage[i]), 3)
        binding_cat[T] = real.binding_category
        source_used[T] = round(float(real.granted_m3.sum() / AVAILABLE_M3), 3)

    packages.append(
        {
            "name": name,
            "sub": sub,
            "grip": [(type(a).name_nl, node) for node, a in steps],
            "nodes": [
                {
                    "name": names[i],
                    "category": CATEGORIES[i],
                    "wet": [wet_peaks[i][T] for T in TS],
                    "dry": [dry_total[i][T] for T in TS],
                    "dry_source": [dry_source[i][T] for T in TS],
                    "coverage": [dry_cov[i][T] for T in TS],
                }
                for i in range(n)
            ],
            "edges": [
                {
                    "to": "buitenwater" if i == n - 1 else names[i + 1],
                    "capacity": caps[i],
                    "inlet": INLETS[i],
                    "hours_full": [edge_full[i][T] for T in TS],
                }
                for i in range(n)
            ],
            "binding_category": [binding_cat[T] for T in TS],
            "source_used": [source_used[T] for T in TS],
        }
    )

print(
    json.dumps(
        {
            "meta": {
                "Ts": TS,
                "storm_vorm": "winter, 96 u, p1a",
                "hours": H,
                "available_mm3": AVAILABLE_M3 / 1e6,
                "drought": REGION
                + " · "
                + SCENARIO
                + " · groeiseizoen 183 d · één bron van "
                + str(round(AVAILABLE_M3 / 1e6))
                + " Mm³, verdeeld via de verdringingsreeks",
                "bron": "18 simulate_network-runs (nat) en 36 allocate-runs (droog: echte en onbeperkte bron per T)",
            },
            "packages": packages,
        }
    )
)
