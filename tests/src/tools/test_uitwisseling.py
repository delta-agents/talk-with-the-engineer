"""Uitwisseling over de systeemgrens: afvoeren en aanvoeren als een transitie.

Twee dingen worden hier vastgelegd. Dat de verhuizing van `pump_capacity_m3_per_sec` naar
een `Connection` een generalisatie is en geen breuk - de eenpolder-casus moet er exact in
zitten, ook bij constructie. En dat de droogtekant dezelfde rekenkern gebruikt met de klem
gespiegeld, met de ankers uit BOUW_WP8_WP10.md Sec. 7.E.
"""

from dataclasses import dataclass

import numpy as np
import pytest

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AanvoerenAction,
    AfvoerenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    simulate,
    simulate_deficit,
    water_level_series,
)

POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}
REFERENCE_STORM = {
    "return_period": 1000,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
    "rainfall_regime": "R",
}


@dataclass(frozen=True)
class Deficit:
    """De exogene droogte, zoals `simulate_deficit` hem verwacht.

    Twee getallen en geen statistiek; zie PLAN_UITWISSELING_EN_NETWERK.md V7.
    """

    deficit_mm_per_day: float
    length_days: int


def _state(**overrides) -> PolderState:
    base = {"area_ha": 4000, "pct_open_water": 3.5, "pump_capacity_m3_per_sec": 5.0}
    return PolderState(**{**base, **overrides})


def _state_with_supply(supply_m3_per_sec: float, **overrides) -> PolderState:
    base = {
        "area_ha": 4000,
        "pct_open_water": 3.5,
        "connections": (
            Connection(
                capacity_out_m3_per_sec=5.0,
                capacity_in_m3_per_sec=supply_m3_per_sec,
            ),
        ),
    }
    return PolderState(**{**base, **overrides})


# --- de verbinding is een generalisatie, geen breuk --------------------------------


def test_a_scalar_pump_capacity_still_constructs_a_state():
    """De constructie-alias: een los getal is een verbinding naar de buitenwereld.

    De toolgrens en een reeks tests geven de capaciteit als kwarg mee. Zonder deze tak zou
    het verhuizen van een veld naar een object een breuk zijn.
    """
    state = _state()
    assert state.pump_capacity_m3_per_sec == 5.0
    assert state.supply_capacity_m3_per_sec == 0.0
    assert state.connections == (Connection(to=OUTSIDE, capacity_out_m3_per_sec=5.0),)
    assert state.connection.is_boundary


def test_the_single_polder_case_is_the_network_with_one_node():
    """`to=OUTSIDE` is de losse polder; dat is de hele afspraak."""
    assert _state().connection.to == OUTSIDE


def test_giving_both_a_scalar_and_connections_is_rejected():
    with pytest.raises(ValueError, match="niet beide"):
        PolderState(
            area_ha=4000,
            pct_open_water=3.5,
            pump_capacity_m3_per_sec=5.0,
            connections=(Connection(capacity_out_m3_per_sec=3.0),),
        )


def test_the_scalar_capacity_raises_with_more_than_one_connection():
    """Een vangrail op een dubbelzinnige vraag, geen beperking op de topologie.

    Twee uitgaande verbindingen naar verschillende bestemmingen: dan heeft "de
    gemaalcapaciteit van deze polder" geen antwoord.
    """
    state = PolderState(
        area_ha=4000,
        pct_open_water=3.5,
        connections=(
            Connection(to="boezem", capacity_out_m3_per_sec=5.0),
            Connection(to="kanaal", capacity_in_m3_per_sec=1.0),
        ),
    )
    with pytest.raises(ValueError, match="2 verbindingen"):
        _ = state.pump_capacity_m3_per_sec


def test_fan_in_does_not_give_the_receiving_node_a_second_connection():
    """A en B lozen beide op C; `connections` bevat alleen uitgaande kanten.

    Dit is de vraag die de property-docstring oproept, dus hij hoort vastgelegd: C houdt
    een verbinding en de scalaire capaciteit blijft dus beantwoordbaar.
    """
    upstream_a = PolderState(
        area_ha=1000,
        pct_open_water=3.5,
        connections=(Connection(to="C", capacity_out_m3_per_sec=2.0),),
    )
    upstream_b = PolderState(
        area_ha=1000,
        pct_open_water=3.5,
        connections=(Connection(to="C", capacity_out_m3_per_sec=3.0),),
    )
    receiving_c = PolderState(
        area_ha=2000,
        pct_open_water=3.5,
        connections=(Connection(to=OUTSIDE, capacity_out_m3_per_sec=6.0),),
    )
    assert upstream_a.pump_capacity_m3_per_sec == 2.0
    assert upstream_b.pump_capacity_m3_per_sec == 3.0
    assert receiving_c.pump_capacity_m3_per_sec == 6.0
    assert len(receiving_c.connections) == 1


# --- een transitie, twee richtingen ------------------------------------------------


def test_discharge_and_supply_share_the_transition_and_differ_only_in_direction():
    state = _state()
    out = AfvoerenAction(delta_pump_capacity_m3_per_sec=2.0).apply(state)
    into = AanvoerenAction(delta_supply_capacity_m3_per_sec=2.0).apply(state)

    assert out.pump_capacity_m3_per_sec == 7.0
    assert out.supply_capacity_m3_per_sec == 0.0
    assert into.pump_capacity_m3_per_sec == 5.0
    assert into.supply_capacity_m3_per_sec == 2.0


def test_the_direction_is_reported_in_words():
    assert AfvoerenAction().direction_label == "outflow"
    assert AanvoerenAction().direction_label == "inflow"


def test_supply_has_no_price_because_the_price_is_a_rationing_question():
    """Zie V8: wat aanvoer kost is het water, niet de inlaat."""
    action = AanvoerenAction(delta_supply_capacity_m3_per_sec=1.0)
    assert action.cost(_state()) is None


def test_supply_capacity_does_not_change_the_storm_answer():
    """Een inlaat helpt niet tegen een bui; de natte kant mag er niet van bewegen."""
    storm = StoreInputGivenH(**REFERENCE_STORM, **POLDER, delta_h_available=1.0)
    without = simulate(_state(), storm)
    with_inlet = simulate(_state_with_supply(2.0), storm)
    assert with_inlet.dh_max_m == pytest.approx(without.dh_max_m, abs=1e-12)


# --- de droogtekant: dezelfde kern, gespiegelde klem -------------------------------


def test_the_old_one_sided_core_cannot_see_a_deficit():
    """Waarom WP8 nodig was: met de eenzijdige klem staat een tekort volledig op nul.

    Dit is geen test van nieuw gedrag maar van de reden dat het gedrag nieuw is.
    """
    deficit_l_s_ha = np.full(168, -0.5)
    levels, _ = water_level_series(deficit_l_s_ha, 140.0, 3860.0, 0.0)
    assert np.allclose(levels, 0.0)


@pytest.mark.parametrize(
    "supply_l_s_ha,shortfall_mm,days_until_empty",
    [(0.0, 109.50, 2.58), (0.3, 31.74, 7.42), (0.4, 5.82, 19.29)],
)
def test_the_deficit_anchors(supply_l_s_ha, shortfall_mm, days_until_empty):
    """BOUW_WP8_WP10.md Sec. 7.E.

    De aanvoernorm van 0,4 l/s/ha levert 86 % van de vraag rechtstreeks, en met de berging
    erbij zit hij op 95 % van de benodigde capaciteit; hij houdt de polder 19 van de 30
    dagen boven de ondergrens. Niet alles, en dat is de uitspraak.
    """
    state = _state_with_supply(supply_l_s_ha * 4000 / 1000, level_margin_m=0.30)
    result = simulate_deficit(state, Deficit(4.0, 30))
    assert result.shortfall_mm == pytest.approx(shortfall_mm, abs=5e-2)
    assert result.days_until_buffer_empty == pytest.approx(days_until_empty, abs=5e-2)


@pytest.mark.parametrize("supply_l_s_ha", [0.0, 0.15, 0.3, 0.4, 0.46])
def test_the_deficit_mass_balance_closes(supply_l_s_ha):
    """Geleverd + uit de berging + tekort = de vraag. Op elke aanvoercapaciteit."""
    state = _state_with_supply(supply_l_s_ha * 4000 / 1000, level_margin_m=0.30)
    result = simulate_deficit(state, Deficit(4.0, 30))
    total = result.supplied_mm + result.buffer_mm + result.shortfall_mm
    assert total == pytest.approx(result.demand_mm, rel=1e-9)


def test_enough_supply_holds_the_target_level():
    """Precies dekkende aanvoer: geen uitzakking, geen tekort."""
    demand_m3_per_sec = 4.0 / 1000 * 4000 * 1e4 / 86400
    state = _state_with_supply(demand_m3_per_sec, level_margin_m=0.30)
    result = simulate_deficit(state, Deficit(4.0, 30))
    assert result.dh_min_m == pytest.approx(0.0, abs=1e-12)
    assert result.shortfall_mm == pytest.approx(0.0, abs=1e-9)
    assert result.days_until_buffer_empty == float("inf")
    assert result.is_covered


def test_the_buffer_is_the_retained_volume_of_the_level_band():
    """De droogtebuffer en `retained_volume_mm` zijn hetzelfde getal.

    0,30 m marge op 3,5 % open water is 0,30 x 0,035 x 1000 = 10,5 mm over de polder. Dat
    twee onafhankelijk bedachte grootheden - de uitlezing uit PLAN_TOOLS_REFACTOR.md Sec.
    8.2 en de klem uit WP8 - op hetzelfde getal uitkomen is de bevestiging dat de peilband
    doet wat hij zegt.
    """
    state = _state_with_supply(0.0, level_margin_m=0.30)
    result = simulate_deficit(state, Deficit(4.0, 30))
    assert result.buffer_mm == pytest.approx(0.30 * 0.035 * 1000, abs=1e-9)
    assert state.replace(target_level_rise_m=0.30).retained_volume_mm == pytest.approx(
        result.buffer_mm, abs=1e-9
    )


def test_without_a_level_margin_every_shortfall_is_immediate():
    """De eerlijke degeneratie van de standaardwaarde: geen buffer is geen uitstel."""
    state = _state_with_supply(0.3 * 4000 / 1000)
    result = simulate_deficit(state, Deficit(4.0, 30))
    assert result.level_margin_m == 0.0
    assert result.dh_min_m == pytest.approx(0.0, abs=1e-12)
    assert result.days_until_buffer_empty == 0.0
    assert result.buffer_mm == pytest.approx(0.0, abs=1e-12)
    assert result.shortfall_mm == pytest.approx(
        result.demand_mm - result.supplied_mm, rel=1e-9
    )


def test_the_deficit_bypasses_the_rainfall_runoff_relation():
    """B4: een tekort is een vraag en geen negatieve afvoer.

    Tabel 39 beschrijft hoe neerslag tot afvoer komt. Daarom mogen `days_to_retain` en
    `retention_fraction` de droogtekant niet raken - vertragen doe je met afvoer, niet met
    vraag.
    """
    plain = simulate_deficit(
        _state_with_supply(1.0, level_margin_m=0.30), Deficit(4.0, 30)
    )
    retained = simulate_deficit(
        _state_with_supply(
            1.0, level_margin_m=0.30, retention_fraction=0.8, days_to_retain=5
        ),
        Deficit(4.0, 30),
    )
    assert retained.shortfall_mm == pytest.approx(plain.shortfall_mm, abs=1e-12)
    assert retained.dh_min_m == pytest.approx(plain.dh_min_m, abs=1e-12)


def test_more_supply_is_monotonically_better():
    """De inverse mag bisecteren, dus de respons moet monotoon zijn."""
    state_at = lambda supply: simulate_deficit(  # noqa: E731
        _state_with_supply(supply, level_margin_m=0.30), Deficit(4.0, 30)
    )
    shortfalls = [state_at(supply).shortfall_mm for supply in np.linspace(0, 2.5, 30)]
    assert np.all(np.diff(shortfalls) <= 1e-9)


def test_supply_never_exceeds_its_capacity_or_the_demand():
    state = _state_with_supply(0.4 * 4000 / 1000, level_margin_m=0.30)
    result = simulate_deficit(state, Deficit(4.0, 30))
    assert (result.supplied_m3_per_sec >= -1e-12).all()
    assert (
        result.supplied_m3_per_sec <= state.supply_capacity_m3_per_sec + 1e-12
    ).all()
