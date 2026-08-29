"""De data achter het waterdraad-prototype: vier runs op een keten van zes gebieden.

Referentie plus cumulatief vasthouden/bergen/afvoeren op Middelblok, in de
trits-volgorde. De uitvoer (JSON op stdout) voedt `docs/plannen/waterdraad.html`;
zie `docs/plannen/NOTITIE_RIDGELINE_STATE.md` ronde 2 voor het idee en de bevindingen.
Draaien: `pixi run python scripts/verkenning_waterdraad.py > /tmp/waterdraad.json`
en de JSON in de const DATA van de html plakken.
"""

import json
import numpy as np
from scipy.stats import gaussian_kde
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
storm = StoreInputGivenH(**BASE, return_period=25, delta_h_available=1.0)

names = ["Hooghout", "Leegveld", "Middelblok", "Zuidplas", "Randwijk", "Boezem"]
areas = [1500.0, 2500.0, 4000.0, 3000.0, 2000.0, 6000.0]
pcts = [2.5, 3.5, 3.0, 4.5, 3.5, 8.0]
caps = [3.0, 5.0, 6.0, 11.0, 13.0, 30.0]
n, TARGET = len(names), 2  # Middelblok


def polders():
    return [
        PolderState(
            area_ha=areas[i],
            pct_open_water=pcts[i],
            connections=(
                Connection(
                    to=OUTSIDE if i == n - 1 else names[i + 1],
                    capacity_out_m3_per_sec=caps[i],
                ),
            ),
        )
        for i in range(n)
    ]


MEASURES = [
    ("referentie", None),
    ("vasthouden", VasthoudenAction(delta_retention_ha=1000)),
    ("bergen", BergenAction(delta_open_water_ha=100)),
    ("afvoeren", AfvoerenAction(delta_pump_capacity_m3_per_sec=4)),
]
runs, state_list = [], polders()
for label, action in MEASURES:
    if action is not None:
        state_list[TARGET] = action.apply(state_list[TARGET])
    runs.append(
        (
            label,
            simulate_network(
                SystemState.from_polders(list(state_list), names=names), storm
            ),
        )
    )

H = 168
allmax = max(float(r.water_level_m[:, :H].max()) for _, r in runs)
grid = np.linspace(-0.05, allmax * 1.08, 90)


def density(series):
    if float(np.std(series)) < 1e-9:
        width = (grid[-1] - grid[0]) / 60.0
        d = np.exp(-0.5 * ((grid - float(series[0])) / width) ** 2)
    else:
        d = gaussian_kde(series, bw_method=0.25)(grid)
        # de staart van de KDE tekent anders een haarlijn boven de echt bereikte piek;
        # de omtrek hoort te eindigen waar de reeks eindigt
        d = np.where(
            (grid >= float(series.min()) - 1e-9) & (grid <= float(series.max()) + 1e-9),
            d,
            0.0,
        )
    return d / d.max()


nodes = [
    {
        "name": names[i],
        "area_ha": areas[i],
        "pct_open_water": pcts[i],
        "area_open_water_ha": round(areas[i] * pcts[i] / 100.0, 1),
        "runs": [],
    }
    for i in range(n)
]
edges = [
    {
        "to": "buitenwater" if i == n - 1 else names[i + 1],
        "capacity": caps[i],
        "runs": [],
    }
    for i in range(n)
]
for label, r in runs:
    levels, exch = r.water_level_m[:, :H], r.exchange_m3_per_sec[:, :H]
    for i in range(n):
        nodes[i]["runs"].append(
            {
                "density": [round(float(d), 4) for d in density(levels[i])],
                "levels": [round(float(v), 4) for v in levels[i]],
                "peak": round(float(levels[i].max()), 3),
            }
        )
        u = exch[i] / caps[i]
        edges[i]["runs"].append(
            {
                "flow": [round(float(v), 3) for v in exch[i]],
                "hours_at_capacity": int((u > 0.999).sum()),
            }
        )

print(
    json.dumps(
        {
            "meta": {
                "storm": "T=25, winter, 96 u, p1a",
                "hours": H,
                "target": names[TARGET],
                "grid": [round(float(g), 4) for g in grid],
                "measures": [m[0] for m in MEASURES],
                "measure_labels": [
                    "referentie",
                    "+ vasthouden (1.000 ha)",
                    "+ bergen (100 ha)",
                    "+ afvoeren (4 m³/s)",
                ],
                "bron": "vier simulate_network-runs; maatregelen cumulatief op Middelblok, in de trits-volgorde",
            },
            "nodes": nodes,
            "edges": edges,
        }
    )
)
