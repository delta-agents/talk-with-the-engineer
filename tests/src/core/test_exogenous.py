"""De forcering als type: wat een `Storm`, een `Deficit` en een rand wel en niet toestaan.

Drie soorten exogene processen, en deze tests leggen vast waarom het er drie zijn. De
grensregel zelf staat in `tests/test_core_boundary.py`; hier gaat het om het gedrag.
"""

import pytest

from talk_with_the_engineer.core.connection import OUTSIDE, single_pump_connection
from talk_with_the_engineer.core.exogenous import (
    UNLIMITED,
    BoundaryCondition,
    Deficit,
    ExogenousEvent,
    Storm,
)
from talk_with_the_engineer.core.reference import REFERENCE_STORM
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.transition import simulate, simulate_deficit

# --- de bui heeft precies een bron voor zijn neerslagsom ------------------------------


def test_a_storm_needs_exactly_one_source_for_its_rainfall_total():
    """Beide of geen van beide is geen bui.

    Aan de toolgrens weigert `RainfallInput` deze combinatie al met een leesbare
    `ModelRetry`. Deze test gaat over de andere aanroeper: een script of een notebook dat de
    kern direct gebruikt. Zonder de controle hier zou die stil de ene weg nemen, en dan is
    niet te zien welk van de twee getallen het antwoord stuurt.
    """
    with pytest.raises(ValueError, match="precies een bron"):
        Storm(
            time_of_year="summer",
            length_event_hrs=192.0,
            name_rainfall_pattern="p1c",
            return_period=10.0,
            rain_volume_mm=60.0,
        )

    with pytest.raises(ValueError, match="precies een bron"):
        Storm(
            time_of_year="summer",
            length_event_hrs=192.0,
            name_rainfall_pattern="p1c",
        )


@pytest.mark.parametrize(
    "extra",
    [{"return_period": 10.0}, {"rain_volume_mm": 60.0}],
)
def test_either_source_on_its_own_is_a_storm(extra):
    storm = Storm(
        time_of_year="summer",
        length_event_hrs=192.0,
        name_rainfall_pattern="p1c",
        **extra,
    )
    assert storm.duration_days == pytest.approx(8.0)


def test_a_storm_is_frozen():
    """Een gebeurtenis die je kunt muteren is geen trekking meer.

    Een rooster over de statistiek maakt varianten; zonder onveranderlijkheid zou een
    variant de referentie kunnen verschuiven en dan rekent de rest van het rooster met een
    andere bui dan er staat.
    """
    with pytest.raises(Exception):
        REFERENCE_STORM.return_period = 100.0


# --- de drie soorten zijn niet uitwisselbaar -----------------------------------------


def test_the_two_events_share_a_duration_and_nothing_else():
    """Het protocol is precies zo breed als de verwantschap.

    Een bui wordt in uren beschreven en een tekort in dagen; wat ze delen is dat de
    transitie over hun duur heen rekent. Een gedeelde basisklasse zou meer beloven.
    """
    deficit = Deficit(deficit_mm_per_day=4.0, length_days=30)

    assert isinstance(REFERENCE_STORM, ExogenousEvent)
    assert isinstance(deficit, ExogenousEvent)
    assert deficit.duration_days == 30.0

    assert not hasattr(deficit, "length_event_hrs")
    assert not hasattr(REFERENCE_STORM, "deficit_mm_per_day")


def test_the_source_volume_is_not_a_property_of_the_drought():
    """Wat de rivier levert hangt niet aan het tekort, en dat is de reden voor twee objecten.

    Dezelfde droogte op een andere bron is een andere doorrekening met hetzelfde
    `Deficit`. Zaten ze in een object, dan was dat twee droogtes.
    """
    assert not hasattr(Deficit(4.0, 30), "available_source_volume_m3")
    assert BoundaryCondition(1e6).available_source_volume_m3 == 1e6


def test_the_unlimited_boundary_is_the_behaviour_of_a_polder_on_its_own():
    """De default zegt hetzelfde als `OUTSIDE`: wat je eruit haalt is er altijd.

    `OUTSIDE` zegt WIE er aan de rand zit en dit WAT hij levert. Dat ze standaard hetzelfde
    zeggen is geen dubbeling maar de aanname die een losse-poldermodel maakt, hier
    opgeschreven op de plek waar hij te veranderen is.
    """
    assert UNLIMITED.is_unlimited
    assert UNLIMITED.available_source_volume_m3 == float("inf")
    assert not BoundaryCondition(0.0).is_unlimited

    state = PolderState(
        area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
    )
    assert state.connection.to == OUTSIDE

    deficit = Deficit(4.0, 30)
    implicit = simulate_deficit(state, deficit)
    explicit = simulate_deficit(state, deficit, UNLIMITED)
    assert implicit.shortfall_mm == pytest.approx(explicit.shortfall_mm, abs=1e-12)


# --- de kern neemt de kernvorm aan en niet een invoermodel ----------------------------


def test_the_transition_reads_the_storm_and_not_a_tool_input_model():
    """`simulate` werkt op een `Storm` zonder dat er een schema in de buurt is.

    Dit is de eigenschap waar de laagregel over gaat, hier als gedrag: geen taal, geen
    validators, geen `assumed_fields` - en toch een antwoord.
    """
    state = PolderState(
        area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
    )
    result = simulate(state, REFERENCE_STORM)
    assert result.dh_max_m > 0.0
    assert not hasattr(REFERENCE_STORM, "language")


def test_a_storm_missing_a_field_is_an_error_and_not_a_silent_default():
    """Een ontbrekend veld hoort te knallen.

    De oude vorm las de forcering met `getattr(storm, veld, default)`, en dan is een
    ontbrekend veld een stille aanname - op twee rekenpaden met twee defaults, wat hetzelfde
    model op twee plekken iets anders laat aannemen.
    """
    with pytest.raises(TypeError):
        Storm(time_of_year="summer", return_period=10.0)  # geen duur, geen patroon
