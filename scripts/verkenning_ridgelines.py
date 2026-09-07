"""Drie ridgeline-verkenningen op echte modeluitvoer: keten, herhaaltijden, maatregelen.

Zie `docs/plannen/NOTITIE_RIDGELINE_STATE.md` voor het idee en de bevindingen.
Draaien: `pixi run python -m pip install matplotlib && pixi run python scripts/verkenning_ridgelines.py docs/images/verkenning`
matplotlib is bewust GEEN projectdependency (zie de opschoning van 2026-08-29); dit is
een verkenningsscript, geen onderdeel van de MCP-server.
"""

import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH
from talk_with_the_engineer.core.actions import (
    AfvoerenAction,
    BergenAction,
    VasthoudenAction,
)
from talk_with_the_engineer.core.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.system import SystemState
from talk_with_the_engineer.core.network import simulate_network
from talk_with_the_engineer.core.transition import simulate

SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
BLUES = [
    "#cde2fb",
    "#9ec5f4",
    "#6da7ec",
    "#3987e5",
    "#256abf",
    "#1c5cab",
    "#104281",
    "#0d366b",
]
CAT = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100"}

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


def styled(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#d8d7d2")
    ax.tick_params(colors=INK2, labelsize=9)
    ax.set_yticks([])


def storm_input(T=1000, **overrides):
    return StoreInputGivenH(
        **{**BASE, **overrides}, return_period=T, delta_h_available=1.0
    )


# ── figuur 1: de keten (SystemState) — tijdreeks-ridgeline per knoop ────────────────
def chain(n):
    names = [f"n{i}" for i in range(n)]
    # stroomafwaarts groeit de capaciteit mee met wat er van boven bijkomt, anders
    # verzadigt de keten en is elke rij gelijk; de rand heeft het boezemgemaal
    capacities = [5.0, 7.5, 10.0, 12.5, 15.0, 20.0][:n]
    polders = [
        PolderState(
            area_ha=4000,
            pct_open_water=3.5,
            connections=(
                Connection(
                    to=OUTSIDE if i == n - 1 else names[i + 1],
                    capacity_out_m3_per_sec=capacities[i],
                ),
            ),
        )
        for i in range(n)
    ]
    return SystemState.from_polders(polders, names=names)


def fig_chain(path):
    n = 6
    result = simulate_network(chain(n), storm_input(T=100))
    levels = result.water_level_m[
        :, :168
    ]  # (knopen, uren); de vlakke staart boeit niet
    hours = np.arange(levels.shape[1])
    step = 0.85 * np.nanmax(levels)
    fig, ax = plt.subplots(figsize=(7.6, 5.4), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    for i in range(n):  # bovenstrooms bovenaan
        y0 = (n - 1 - i) * step
        ridge = levels[i]
        color = BLUES[2 + i % 6]
        ax.fill_between(
            hours, y0, y0 + ridge, color=color, alpha=0.85, zorder=2 + i, lw=0
        )
        ax.plot(hours, y0 + ridge, color=SURFACE, lw=2.4, zorder=2 + i)
        ax.plot(hours, y0 + ridge, color=color, lw=1.4, zorder=2 + i)
        label = (
            "knoop 1 · bovenstrooms"
            if i == 0
            else ("knoop 6 · loost op de rand" if i == n - 1 else f"knoop {i + 1}")
        )
        ax.text(-3, y0 + 0.02, label, ha="right", va="bottom", fontsize=9, color=INK2)
        peak = int(np.argmax(ridge))
        ax.annotate(
            f"{ridge[peak]:.2f} m",
            (hours[peak], y0 + ridge[peak]),
            xytext=(-6, 3),
            textcoords="offset points",
            ha="right",
            fontsize=8,
            color=INK,
            zorder=30,
            bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.85),
        )
    styled(ax)
    ax.set_xlim(hours[0], hours[-1])
    ax.set_xlabel("uur sinds het begin van de bui", color=INK2, fontsize=9)
    ax.set_title(
        "De keten als ridgeline: zes knopen, één bui (T=100)\n"
        "wat de ene knoop wegpompt, komt bij de volgende binnen",
        loc="left",
        fontsize=10.5,
        color=INK,
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)


# ── figuur 2: herhaaltijden — categorical ridgeline van waterstandsverdelingen ──────
def fig_return_periods(path):
    Ts = [2, 5, 10, 25, 50, 100, 500, 1000]
    fig, ax = plt.subplots(figsize=(7.6, 5.4), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    grid = np.linspace(-0.35, 2.35, 460)
    step = 0.75
    for i, T in enumerate(Ts):  # kleinste T onderaan
        inp = storm_input(T=T)
        r = simulate(PolderState.from_water_system_input(inp), inp)
        kde = gaussian_kde(r.water_level_m, bw_method=0.25)
        dens = kde(grid)
        dens = dens / dens.max() * 1.55  # scale ~ ggridges: bewuste overlap
        y0 = i * step
        color = BLUES[i]
        ax.fill_between(
            grid, y0, y0 + dens, color=color, alpha=0.9, zorder=10 - i, lw=0
        )
        ax.plot(grid, y0 + dens, color=SURFACE, lw=2.2, zorder=10 - i)
        ax.plot(
            grid, y0 + dens, color=color if i > 1 else "#6da7ec", lw=1.3, zorder=10 - i
        )
        ax.text(
            -0.35,
            y0 + 0.04,
            f"T = {T}",
            ha="right",
            va="bottom",
            fontsize=9,
            color=INK2,
        )
        ax.plot([r.dh_max_m], [y0], marker="o", ms=5, color=INK, zorder=30)
        ax.annotate(
            f"piek {r.dh_max_m:.2f}",
            (r.dh_max_m, y0),
            xytext=(6, -10),
            textcoords="offset points",
            fontsize=7.5,
            color=INK,
            zorder=30,
            bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.85),
        )
    styled(ax)
    ax.set_xlim(-0.5, 2.35)
    ax.set_xlabel(
        "waterstand boven streefpeil [m], verdeling over de bui-uren",
        color=INK2,
        fontsize=9,
    )
    ax.set_title(
        "Herhaaltijden als ridgeline: dezelfde polder, acht buien\n"
        "hoe de waterstandsverdeling opschuift met de terugkeertijd — de stip is de piek (dh_max)",
        loc="left",
        fontsize=10.5,
        color=INK,
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)


# ── figuur 3: maatregelen — identiteit, elk zijn eigen tijdreeks-ridge ───────────────
def fig_measures(path):
    inp = storm_input(T=1000)
    base = PolderState.from_water_system_input(inp)
    rows = [
        ("referentie · niets doen", base, INK2),
        (
            "vasthouden · 1.200 ha land",
            VasthoudenAction(delta_retention_ha=1200).apply(base),
            CAT["aqua"],
        ),
        (
            "bergen · +150 ha open water",
            BergenAction(delta_open_water_ha=150).apply(base),
            CAT["orange"],
        ),
        (
            "afvoeren · +5 m³/s gemaal",
            AfvoerenAction(delta_pump_capacity_m3_per_sec=5).apply(base),
            CAT["blue"],
        ),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 5.0), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    results = [(label, simulate(state, inp), color) for label, state, color in rows]
    horizon = max(len(r.water_level_m) for _, r, _ in results)

    def padded(series):
        return np.pad(series, (0, horizon - len(series)), mode="edge")

    ref = padded(results[0][1].water_level_m)
    hours = np.arange(horizon)
    step = 0.95 * np.nanmax(ref)
    for i, (label, r, color) in enumerate(results):
        y0 = (len(rows) - 1 - i) * step
        if i > 0:  # referentie als spook achter elke maatregel
            ax.fill_between(
                hours, y0, y0 + ref, color="#d8d7d2", alpha=0.55, zorder=2 * i, lw=0
            )
        ridge = padded(r.water_level_m)
        ax.fill_between(
            hours, y0, y0 + ridge, color=color, alpha=0.8, zorder=2 * i + 1, lw=0
        )
        ax.plot(hours, y0 + ridge, color=SURFACE, lw=2.2, zorder=2 * i + 1)
        ax.plot(hours, y0 + ridge, color=color, lw=1.4, zorder=2 * i + 1)
        ax.text(-3, y0 + 0.02, label, ha="right", va="bottom", fontsize=9, color=INK2)
        ax.annotate(
            f"piek {r.dh_max_m:.2f} m",
            (int(np.argmax(ridge)), y0 + np.max(ridge)),
            xytext=(4, 2),
            textcoords="offset points",
            fontsize=8,
            color=INK,
        )
    styled(ax)
    ax.set_xlim(0, horizon - 1)
    ax.set_xlabel(
        "uur sinds het begin van de bui · grijs = referentie zonder maatregel",
        color=INK2,
        fontsize=9,
    )
    ax.set_title(
        "Maatregelen als ridgeline: één bui, vier toestanden\n"
        "grijs is de referentie; elke maatregel neemt er zijn eigen deel van weg",
        loc="left",
        fontsize=10.5,
        color=INK,
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)


out = sys.argv[1]
fig_chain(f"{out}/ridgeline-keten.png")
fig_return_periods(f"{out}/ridgeline-herhaaltijden.png")
fig_measures(f"{out}/ridgeline-maatregelen.png")
print("klaar")
