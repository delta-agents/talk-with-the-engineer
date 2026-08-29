"""De data achter het waterdraad-prototype: twee pakketten, elk vier cumulatieve runs.

Geconcentreerd (alle maatregelen op Middelblok) tegenover gespreid (dezelfde
maatregelen, uitgesplitst over de keten), beide cumulatief in de trits-volgorde.
De uitvoer (JSON op stdout) voedt `docs/plannen/waterdraad.html`; zie
`docs/plannen/NOTITIE_RIDGELINE_STATE.md` ronde 2 en 3 voor idee en bevindingen.
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
n = len(names)
H = 168


def fresh_polders():
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


STEP_LABELS = ["referentie", "+ vasthouden", "+ bergen", "+ afvoeren"]
PACKAGES = [
    {
        "name": "geconcentreerd",
        "sub": "alle drie de maatregelen op Middelblok",
        "steps": [
            ("vasthouden", "Middelblok", VasthoudenAction(delta_retention_ha=1000)),
            ("bergen", "Middelblok", BergenAction(delta_open_water_ha=100)),
            (
                "afvoeren",
                "Middelblok",
                AfvoerenAction(delta_pump_capacity_m3_per_sec=4),
            ),
        ],
    },
    {
        "name": "gespreid",
        "sub": "dezelfde maatregelen, uitgesplitst over de keten",
        "steps": [
            ("vasthouden", "Leegveld", VasthoudenAction(delta_retention_ha=1000)),
            ("bergen", "Middelblok", BergenAction(delta_open_water_ha=100)),
            ("afvoeren", "Randwijk", AfvoerenAction(delta_pump_capacity_m3_per_sec=4)),
        ],
    },
]

results = []
for pkg in PACKAGES:
    state_list = fresh_polders()
    runs = [
        simulate_network(SystemState.from_polders(list(state_list), names=names), storm)
    ]
    for _, node_name, action in pkg["steps"]:
        idx = names.index(node_name)
        state_list[idx] = action.apply(state_list[idx])
        runs.append(
            simulate_network(
                SystemState.from_polders(list(state_list), names=names), storm
            )
        )
    results.append(runs)

allmax = max(float(r.water_level_m[:, :H].max()) for runs in results for r in runs)
grid = np.linspace(-0.05, allmax * 1.08, 90)


def density(series):
    if float(np.std(series)) < 1e-9:
        width = (grid[-1] - grid[0]) / 60.0
        d = np.exp(-0.5 * ((grid - float(series[0])) / width) ** 2)
    else:
        d = gaussian_kde(series, bw_method=0.25)(grid)
        d = np.where(
            (grid >= float(series.min()) - 1e-9) & (grid <= float(series.max()) + 1e-9),
            d,
            0.0,
        )
    return d / d.max()


packages = []
for p, pkg in enumerate(PACKAGES):
    nodes, edges = [], []
    for i in range(n):
        node_runs = []
        for r in results[p]:
            levels = r.water_level_m[i, :H]
            node_runs.append(
                {
                    "density": [round(float(d), 4) for d in density(levels)],
                    "levels": [round(float(v), 4) for v in levels],
                    "peak": round(float(levels.max()), 3),
                }
            )
        nodes.append(
            {
                "name": names[i],
                "area_ha": areas[i],
                "area_open_water_ha": round(areas[i] * pcts[i] / 100.0, 1),
                "runs": node_runs,
            }
        )
        final = results[p][-1]
        exch = final.exchange_m3_per_sec[i, :H]
        u = exch / caps[i]
        edges.append(
            {
                "to": "buitenwater" if i == n - 1 else names[i + 1],
                "capacity": caps[i],
                "flow": [round(float(v), 3) for v in exch],
                "hours_at_capacity": int((u > 0.999).sum()),
            }
        )
    packages.append(
        {
            "name": pkg["name"],
            "sub": pkg["sub"],
            "grip": [(m, node) for m, node, _ in pkg["steps"]],
            "nodes": nodes,
            "edges": edges,
        }
    )

print(
    json.dumps(
        {
            "meta": {
                "storm": "T=25, winter, 96 u, p1a",
                "hours": H,
                "grid": [round(float(g), 4) for g in grid],
                "step_labels": STEP_LABELS,
                "bron": "acht simulate_network-runs: twee pakketten, elk cumulatief in de trits-volgorde",
            },
            "packages": packages,
        }
    )
)
