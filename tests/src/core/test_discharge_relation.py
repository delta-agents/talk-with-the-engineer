"""De neerslag-afvoerrelatie hoort bij het gebied, en dus mogen gebieden erin verschillen.

`days_to_discharge` is hoe snel de dagneerslag op dit gebied tot regionale afvoer komt:
bodem en drainage, niet het weer. Deze tests leggen de twee gevolgen vast die daaruit
volgen - dat een cascade knopen met verschillende karakteristieken kan hebben, en dat de
droge kant het veld niet kent.
"""

import numpy as np
import pytest

from talk_with_the_engineer.core.connection import Connection, single_pump_connection
from talk_with_the_engineer.core.exogenous import Deficit
from talk_with_the_engineer.core.network import node_forcing, simulate_network
from talk_with_the_engineer.core.reference import REFERENCE_STORM
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.system import SystemState
from talk_with_the_engineer.core.transition import simulate, simulate_deficit


def make_polder(days_to_discharge, drains_to=None, **overrides):
    connections = (
        single_pump_connection(1.5)
        if drains_to is None
        else (Connection(to=drains_to, capacity_out_m3_per_sec=1.5),)
    )
    return PolderState(
        area_ha=1000,
        pct_open_water=5.0,
        connections=connections,
        days_to_discharge=days_to_discharge,
        **overrides,
    )


# --- het is een eigenschap van het gebied --------------------------------------------


def test_fewer_days_concentrates_the_discharge_and_raises_the_peak():
    """Monotonie, en de richting is het punt.

    Over minder dagen tot afvoer komen betekent dat dezelfde neerslag in een korter venster
    op het open water landt. Een traag gebied heeft dus een lagere piek dan een snel gebied
    onder exact dezelfde bui - en dat is precies waarom dit geen eigenschap van de bui kan
    zijn.
    """
    peaks = [
        simulate(make_polder(days), REFERENCE_STORM).dh_max_m for days in (2, 3, 4)
    ]
    assert peaks[0] > peaks[1] > peaks[2]


def test_the_simulation_reports_the_relation_it_used():
    """De uitkomst draagt de karakteristiek waarmee is gerekend.

    Zonder dat veld zou een tool het uit de bui moeten halen, en daar staat het niet meer.
    """
    result = simulate(make_polder(4), REFERENCE_STORM)
    assert result.days_to_discharge == 4


def test_the_dry_side_does_not_know_the_relation():
    """Een tekort is geen negatieve afvoer maar een vraag, en die komt onvertraagd.

    Twee polders die alleen in hun afvoerkarakteristiek verschillen, geven op de droge kant
    tot op de bit hetzelfde antwoord. Zou dat niet zo zijn, dan liet de droge kant zich
    sturen door een grootheid die er niets over zegt.
    """
    deficit = Deficit(4.0, 30)
    fast = simulate_deficit(make_polder(2, level_margin_m=0.3), deficit)
    slow = simulate_deficit(make_polder(4, level_margin_m=0.3), deficit)
    assert fast.shortfall_mm == pytest.approx(slow.shortfall_mm, abs=1e-12)
    assert fast.buffer_mm == pytest.approx(slow.buffer_mm, abs=1e-12)


# --- en dus mogen de knopen in een cascade verschillen --------------------------------


def test_a_cascade_can_mix_fast_and_slow_areas():
    """Twee knopen, verschillende karakteristiek, en de forcering verschilt dus per knoop.

    Dit is wat de grootheid op de toestand mogelijk maakt: een traag veengebied en een snel
    zandgebied onder dezelfde bui. Toen hij aan de bui hing, deelde het hele systeem er een.
    """
    system = SystemState.from_polders(
        [make_polder(2, drains_to="boezem"), make_polder(4)],
        names=("snel", "boezem"),
    )
    runoff, _ = node_forcing(system, REFERENCE_STORM)

    assert runoff.shape[0] == 2
    assert not np.allclose(runoff[0], runoff[1])
    # het snelle gebied heeft de hogere piekafvoer, en dezelfde totale hoeveelheid
    assert runoff[0].max() > runoff[1].max()
    assert runoff[0].sum() == pytest.approx(runoff[1].sum(), rel=1e-6)


def test_areas_with_the_same_relation_share_one_series():
    """Groeperen op het paar (afvoerduur, vertraging) en niet per knoop rekenen.

    Een lus over duizenden knopen is precies wat de vectorisatie over de breedte moet
    vermijden. Deze test toetst het GEDRAG dat de groepering hoort te hebben: knopen met
    dezelfde twee waarden krijgen dezelfde reeks, tot op de bit.
    """
    system = SystemState.from_polders(
        [
            make_polder(3, drains_to="boezem"),
            make_polder(3, drains_to="boezem"),
            make_polder(3),
        ],
        names=("a", "b", "boezem"),
    )
    runoff, _ = node_forcing(system, REFERENCE_STORM)
    assert np.array_equal(runoff[0], runoff[1])
    assert np.array_equal(runoff[0], runoff[2])


def test_the_direct_precipitation_is_the_same_for_every_node():
    """Neerslag die op open water valt hangt van geen van de twee gebiedsgrootheden af.

    Hij komt uit dezelfde opzoeking als de afvoerreeks, dus deze test bewaakt dat het
    per-knoop uitrekenen van die reeks hem niet per ongeluk laat meevariëren.
    """
    system = SystemState.from_polders(
        [make_polder(2, drains_to="boezem"), make_polder(4)],
        names=("snel", "boezem"),
    )
    _, direct = node_forcing(system, REFERENCE_STORM)
    assert np.array_equal(direct[0], direct[1])


def test_the_round_trip_through_the_system_keeps_the_relation():
    """`from_polders` en `to_polders` verliezen het veld niet.

    De heen-en-weer is hoe de cascadetool een knoop los doorrekent om het koppeleffect te
    meten; verliest hij hier de karakteristiek, dan vergelijkt die meting twee gebieden.
    """
    polders = [make_polder(2, drains_to="boezem"), make_polder(4)]
    system = SystemState.from_polders(polders, names=("snel", "boezem"))
    back = system.to_polders()
    assert [p.days_to_discharge for p in back] == [2, 4]


def test_a_mixed_cascade_still_computes():
    """Het geheel doet het ook echt, en niet alleen de forcering.

    Een rooktest op de volledige doorrekening: gemengde karakteristieken door de passes
    heen, met een eindige opvoerhoogte zodat de terugkoppeling meedoet.
    """
    system = SystemState.from_polders(
        [
            make_polder(2, drains_to="boezem"),
            make_polder(4, drains_to="boezem"),
            make_polder(3),
        ],
        names=("veen", "zand", "boezem"),
    )
    result = simulate_network(system, REFERENCE_STORM)
    assert result.dh_max_m.shape == (3,)
    assert np.all(result.dh_max_m > 0.0)
