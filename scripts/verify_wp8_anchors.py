"""Ankergetallen voor docs/plannen/BOUW_WP8_WP10.md §7 opnieuw uitrekenen.

Dit script bestaat om één reden: het bouwdocument bevat getallen waartegen WP8, WP9 en
WP10 gebouwd worden, en die getallen moeten na te rekenen zijn zonder ze te vertrouwen.
Draai het vóór de bouw tegen de huidige kern, en na de bouw opnieuw. Verschuift er een
anker, dan is dat een gedragsverandering en die hoort bedoeld te zijn.

    .pixi/envs/default/bin/python scripts/verify_wp8_anchors.py

De prototypes hieronder zijn geen productiecode. `clamped_scan` en `slack_of` staan hier
in hun kortste vorm zodat te zien is dat de ankers uit precies deze definities volgen; de
implementatie in `simulate.py` moet ze reproduceren, niet ervan afwijken.
"""

import itertools
import sys
import time

import numpy as np

from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.transition import (
    HOURS_PER_DAY,
    simulate,
    to_hourly,
)

REFERENCE_STORM = dict(
    return_period=1000,
    time_of_year="winter",
    length_event_hrs=96.0,
    name_rainfall_pattern="p1a",
    days_to_discharge=4,
    rainfall_regime="R",
)
REFERENCE_POLDER = dict(
    area_ha=4000, percentage_open_water=3.5, discharge_capacity_m3_per_sec=5
)

DH_MAX_PRODUCTION_M = 1.8057576857142845
"""Anker A. De productiebalans, dus mét krimpend land en directe neerslag."""

failures: list[str] = []


def check(label: str, value: float, expected: float, tolerance: float, unit: str = ""):
    ok = abs(value - expected) <= tolerance
    mark = "ok  " if ok else "FOUT"
    print(f"  [{mark}] {label:52s} {value:14.6g} {unit}")
    if not ok:
        failures.append(f"{label}: {value!r} != {expected!r} (tol {tolerance:g})")


# --- de twee primitieven uit docs/plannen/BOUW_WP8_WP10.md B1 -------------------------------------


def clamped_scan(delta, lo, hi, h0=0.0):
    """h[t] = clamp(h[t-1] + delta[t], lo, hi), als associative scan over de laatste as.

    Geklemde translaties `f(x) = clamp(x + a, l, u)` zijn gesloten onder compositie:

        combine((a1,l1,u1), (a2,l2,u2)) = (a1+a2,
                                           clamp(l1+a2, l2, u2),
                                           clamp(u1+a2, l2, u2))

    Dat is associatief, dus de recursie is een prefix-scan met log-diepte.
    """
    length = delta.shape[-1]
    a = np.asarray(delta, dtype=float).copy()
    low = np.full(a.shape, lo, dtype=float)
    high = np.full(a.shape, hi, dtype=float)
    step = 1
    while step < length:
        a2 = a[..., step:].copy()
        l2, u2 = low[..., step:].copy(), high[..., step:].copy()
        a1 = a[..., :-step]
        l1, u1 = low[..., :-step], high[..., :-step]
        a[..., step:] = a1 + a2
        low[..., step:] = np.minimum(np.maximum(l1 + a2, l2), u2)
        high[..., step:] = np.minimum(np.maximum(u1 + a2, l2), u2)
        step *= 2
    return np.minimum(np.maximum(h0 + a, low), high)


def clamped_recursion(delta, lo, hi, h0=0.0):
    """Dezelfde recursie als lus. Alleen om `clamped_scan` tegen te toetsen."""
    out = np.empty(len(delta))
    level = h0
    for index, step in enumerate(delta):
        level = min(max(level + step, lo), hi)
        out[index] = level
    return out


def slack_of(levels, delta, h0=0.0):
    """Wat de klem heeft toegevoegd (>0) of weggenomen (<0), per tijdstap."""
    previous = np.concatenate([[h0], levels[:-1]])
    return levels - (previous + delta)


# --- de referentiecasus, ontleed in de termen die `simulate` gebruikt ------------------


def state_of_reference():
    return PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5.0)


def hourly_delta(state, storm_kwargs):
    """De uurlijkse peilverandering bij een gemaal op capaciteit, exact zoals `simulate`.

    Twee termen: het land dat afvoert, en de neerslag die direct op het open water valt.
    """
    model = StoreInputGivenH(**storm_kwargs, **REFERENCE_POLDER, delta_h_available=1.0)
    result = simulate(state, model)
    metres_per_m3_per_sec = 3600.0 / (state.area_open_water_ha * 1e4)
    inflow = result.drainage_l_s_ha * state.area_land_ha * 1e-3
    delta = (inflow - state.pump_capacity_m3_per_sec) * metres_per_m3_per_sec
    per_hour_m = to_hourly(result.rainfall_on_water_per_day_mm / HOURS_PER_DAY) / 1000.0
    direct = np.zeros(len(delta))
    overlap = min(len(per_hour_m), len(direct))
    direct[:overlap] = per_hour_m[:overlap]
    return delta + direct, result, metres_per_m3_per_sec


# --- de ankers ------------------------------------------------------------------------


def anchor_a(state):
    print("\nA - invariant")
    delta, result, _ = hourly_delta(state, REFERENCE_STORM)
    check("dh_max referentiecasus", result.dh_max_m, DH_MAX_PRODUCTION_M, 1e-12, "m")
    check(
        "leegmaalsnelheid 5 m3/s op 140 ha",
        5.0 * 86400 / (140 * 1e4),
        0.30857,
        1e-4,
        "m/dag",
    )
    return delta, result


def anchor_b(state):
    print("\nB - clamped_scan(lo=0, hi=+inf) == water_level_series, hele invoerruimte")
    worst, count = 0.0, 0
    for season, length, period, pattern, days in itertools.product(
        ["winter", "summer"],
        [48.0, 96.0, 192.0],
        [10, 100, 1000],
        ["p_0", "p1a", "p1c", "p2b"],
        [2, 3, 4],
    ):
        delta, result, _ = hourly_delta(
            state,
            dict(
                return_period=period,
                time_of_year=season,
                length_event_hrs=length,
                name_rainfall_pattern=pattern,
                days_to_discharge=days,
                rainfall_regime="R",
            ),
        )
        worst = max(
            worst,
            float(
                np.abs(clamped_scan(delta, 0.0, np.inf) - result.water_level_m).max()
            ),
        )
        count += 1
    check(f"grootste afwijking over {count} combinaties", worst, 0.0, 1e-12, "m")


def anchor_c(delta):
    print("\nC - tweezijdige scan == de sequentiele lus")
    for lo, hi in [
        (0.0, np.inf),
        (-0.30, np.inf),
        (-np.inf, 0.0),
        (-0.30, 0.0),
        (-0.20, 0.20),
    ]:
        difference = float(
            np.abs(clamped_scan(delta, lo, hi) - clamped_recursion(delta, lo, hi)).max()
        )
        check(f"lo={lo:g} hi={hi:g}", difference, 0.0, 1e-12, "m")


def anchor_d(delta):
    print("\nD - voorbemaling verzadigt op de leegmaalsnelheid van het gemaal")
    base = float(clamped_scan(delta, 0.0, np.inf).max())
    expected = {
        0.05: 5.0000,
        0.10: 10.0000,
        0.20: 10.5130,
        0.30: 10.5130,
        1.00: 10.5130,
    }
    for margin, gain_cm in expected.items():
        peak = float(clamped_scan(delta, -margin, np.inf).max())
        check(
            f"marge {margin * 100:.0f} cm -> winst",
            (base - peak) * 100,
            gain_cm,
            5e-4,
            "cm",
        )


def anchor_e(state):
    print("\nE - droogte: tekort 4 mm/dag, 30 dagen, level_margin_m = 0,30")
    deficit_mm_per_day, days, margin = 4.0, 30, 0.30
    area_open_water_m2 = state.area_open_water_ha * 1e4
    metres_per_m3_per_sec = 3600.0 / area_open_water_m2
    demand_land = deficit_mm_per_day / 1000 * state.area_land_ha * 1e4 / 86400
    demand_open_water_m_per_hour = deficit_mm_per_day / 1000 / 24
    demand_total = demand_land + deficit_mm_per_day / 1000 * area_open_water_m2 / 86400
    check("totale vraag", demand_total, 1.8519, 1e-3, "m3/s")

    hours = days * 24
    expected = {  # inlaat l/s/ha over de polder -> (tekort mm, dagen tot bodem)
        0.0: (109.50, 2.58),
        0.3: (31.74, 7.42),
        0.4: (5.82, 19.29),
    }
    for norm, (shortfall_mm, days_to_floor) in expected.items():
        inlet = norm * state.area_ha / 1000
        delta = np.full(
            hours,
            (inlet - demand_land) * metres_per_m3_per_sec
            - demand_open_water_m_per_hour,
        )
        levels = clamped_scan(delta, -margin, 0.0)
        slack = slack_of(levels, delta)
        unmet_mm = float(
            slack[slack > 0].sum() * area_open_water_m2 / (state.area_ha * 1e4) * 1000
        )
        on_floor = levels <= -margin + 1e-12
        reached = float(np.argmax(on_floor) / 24) if on_floor.any() else float("inf")
        check(f"inlaat {norm:.1f} l/s/ha -> tekort", unmet_mm, shortfall_mm, 5e-2, "mm")
        check(
            f"inlaat {norm:.1f} l/s/ha -> bodem na",
            reached,
            days_to_floor,
            5e-2,
            "dagen",
        )
        supplied_mm = inlet * hours * 3600 / (state.area_ha * 1e4) * 1000
        buffer_mm = margin * state.area_open_water_ha / state.area_ha * 1000
        check(
            f"inlaat {norm:.1f} l/s/ha -> massabalans",
            supplied_mm + buffer_mm + unmet_mm,
            deficit_mm_per_day * days,
            5e-2,
            "mm",
        )


def anchor_f(state, delta, result):
    print("\nF - slack generaliseert de pumped-reeks")
    metres_per_m3_per_sec = 3600.0 / (state.area_open_water_ha * 1e4)
    levels = clamped_scan(delta, 0.0, np.inf)
    slack = slack_of(levels, delta)
    pumped = state.pump_capacity_m3_per_sec - slack / metres_per_m3_per_sec
    check(
        "|pumped uit slack - pumped_m3_per_sec|",
        float(np.abs(pumped - result.pumped_m3_per_sec).max()),
        0.0,
        1e-12,
        "m3/s",
    )
    inflow_m3 = float(
        (result.drainage_l_s_ha * state.area_land_ha * 1e-3).sum() * 3600
        + (
            delta
            - (
                result.drainage_l_s_ha * state.area_land_ha * 1e-3
                - state.pump_capacity_m3_per_sec
            )
            * metres_per_m3_per_sec
        ).sum()
        / metres_per_m3_per_sec
        * 3600
    )
    closed = (
        inflow_m3 - pumped.sum() * 3600 - levels[-1] * state.area_open_water_ha * 1e4
    )
    check("massabalans aanvoer - gepompt - berging", closed, 0.0, 1e-6, "m3")
    only_at_clamp = bool(np.all((np.abs(slack) <= 1e-15) | (levels <= 1e-15)))
    print(f"  [{'ok  ' if only_at_clamp else 'FOUT'}] slack != 0 alleen op een klem")
    if not only_at_clamp:
        failures.append("slack is niet-nul buiten een klem")


def anchor_g(delta):
    print("\nG - schaal: vectoriseer de breedte, niet de diepte")
    for nodes in (100, 1000, 8500):
        stacked = np.tile(delta, (nodes, 1))
        start = time.perf_counter()
        for _ in range(5):
            clamped_scan(stacked, -0.30, 0.0)
        elapsed = (time.perf_counter() - start) / 5
        print(
            f"  [info] {nodes:5d} knopen x {stacked.shape[1]} uur, tweezijdig"
            f"{elapsed * 1000:12.1f} ms ({elapsed / nodes * 1e6:.2f} us/knoop)"
        )


def main():
    state = state_of_reference()
    delta, result = anchor_a(state)
    anchor_b(state)
    anchor_c(delta)
    anchor_d(delta)
    anchor_e(state)
    anchor_f(state, delta, result)
    anchor_g(delta)

    print()
    if failures:
        print(f"{len(failures)} anker(s) verschoven:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("alle ankers staan waar docs/plannen/BOUW_WP8_WP10.md ze zet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
