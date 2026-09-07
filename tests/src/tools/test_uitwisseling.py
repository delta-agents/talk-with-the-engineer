"""Uitwisseling over de systeemgrens: afvoeren en aanvoeren als een transitie.

Twee dingen worden hier vastgelegd. Dat een `Connection` de losse polder als kleinste
instantie bevat - een scalaire `pump_capacity_m3_per_sec` moet er exact in zitten, ook bij
constructie. En dat de droogtekant dezelfde rekenkern gebruikt met de klem gespiegeld, met
dezelfde ankers als de natte kant.
"""

import numpy as np
import pytest

from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH
from talk_with_the_engineer.core.exogenous import BoundaryCondition, Deficit
from talk_with_the_engineer.core.actions import (
    SupplyAction,
    DischargeAction,
)
from talk_with_the_engineer.core.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.inverse import solve_supply
from talk_with_the_engineer.core.transition import (
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
    out = DischargeAction(delta_pump_capacity_m3_per_sec=2.0).apply(state)
    into = SupplyAction(delta_supply_capacity_m3_per_sec=2.0).apply(state)

    assert out.pump_capacity_m3_per_sec == 7.0
    assert out.supply_capacity_m3_per_sec == 0.0
    assert into.pump_capacity_m3_per_sec == 5.0
    assert into.supply_capacity_m3_per_sec == 2.0


def test_the_direction_is_reported_in_words():
    assert DischargeAction().direction_label == "outflow"
    assert SupplyAction().direction_label == "inflow"


def test_supply_has_no_price_because_the_price_is_a_rationing_question():
    """Wat aanvoer kost is het water en niet de inlaat; dat is een verdringingsvraag."""
    action = SupplyAction(delta_supply_capacity_m3_per_sec=1.0)
    assert action.cost(_state()) is None


def test_supply_capacity_does_not_change_the_storm_answer():
    """Een inlaat helpt niet tegen een bui; de natte kant mag er niet van bewegen."""
    storm = StoreInputGivenH(**REFERENCE_STORM, **POLDER, delta_h_available=1.0)
    without = simulate(_state(), storm)
    with_inlet = simulate(_state_with_supply(2.0), storm)
    assert with_inlet.dh_max_m == pytest.approx(without.dh_max_m, abs=1e-12)


# --- de droogtekant: dezelfde kern, gespiegelde klem -------------------------------


def test_a_one_sided_clamp_cannot_see_a_deficit():
    """Waarom de klem tweezijdig moet zijn: met één grens staat een tekort volledig op nul.

    Dit toetst geen gedrag van de tools maar de reden dat de balans twee grenzen heeft.
    `water_level_series` met alleen een ondergrens op nul kapt elke uitzakking weg, dus een
    negatieve forcering levert een vlakke reeks - een polder die niets merkt van dertig
    dagen droogte.
    """
    deficit_l_s_ha = np.full(168, -0.5)
    levels, _ = water_level_series(deficit_l_s_ha, 140.0, 3860.0, 0.0)
    assert np.allclose(levels, 0.0)


@pytest.mark.parametrize(
    "supply_l_s_ha,shortfall_mm,days_until_empty",
    [(0.0, 109.50, 2.58), (0.3, 31.74, 7.42), (0.4, 5.82, 19.29)],
)
def test_the_deficit_anchors(supply_l_s_ha, shortfall_mm, days_until_empty):
    """Het anker op de droge kant.

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
    twee onafhankelijk bedachte grootheden - de statische uitlezing `retained_volume_mm` en
    de dynamische klem in `simulate_deficit` - op hetzelfde getal uitkomen is de bevestiging
    dat de peilband doet wat hij zegt.
    """
    state = _state_with_supply(0.0, level_margin_m=0.30)
    result = simulate_deficit(state, Deficit(4.0, 30))
    assert result.buffer_mm == pytest.approx(0.30 * 0.035 * 1000, abs=1e-9)
    assert state.replace(target_level_rise_m=0.30).retained_volume_mm == pytest.approx(
        result.buffer_mm, abs=1e-9
    )


def test_the_level_band_reaches_the_state_through_the_tool_boundary():
    """De peilband is invoer geworden, en dat was hij niet.

    `WaterSystemInput` hield gemaalcapaciteit, oppervlak en open water bij, maar niets over
    het peil. Daardoor stond de band via elke tool altijd op [0, 0] en kon een beller niet
    zeggen dat zijn polder al is opgezet of al voormaalt - terwijl de zoeker peilopzet wél
    als maatregel aanbood. Dit is CONTEXT en geen maatregel: het zet de startstand.

    """
    reference = {
        "area_ha": 4000,
        "percentage_open_water": 3.5,
        "discharge_capacity_m3_per_sec": 5,
        "return_period": 100,
        "delta_h_available": 1.0,
    }
    plain = PolderState.from_water_system_input(StoreInputGivenH(**reference))
    raised = PolderState.from_water_system_input(
        StoreInputGivenH(**reference, target_level_rise_m=0.20, level_margin_m=0.10)
    )

    assert (plain.target_level_rise_m, plain.level_margin_m) == (0.0, 0.0)
    assert (raised.target_level_rise_m, raised.level_margin_m) == (0.20, 0.10)
    # en de opzet telt meteen mee in de voorraad, zonder dat er een maatregel aan te pas kwam
    assert raised.retained_volume_mm == pytest.approx(0.20 * 0.035 * 1000, abs=1e-9)


def test_raising_the_target_level_deepens_the_drought_buffer():
    """Peilopzet koopt aan de droge kant precies zijn eigen centimeters buffer.

    De waterstand wordt gemeten ten opzichte van het streefpeil, en dat streefpeil kan
    opgezet zijn. Een polder die 20 cm hoger staat kan die 20 cm uitzakken naar het
    oorspronkelijke peil. Stond in de klem alleen de peilmarge, dan zou peilopzet - de enige
    maatregel die voorraad KOOPT - aan de droge kant niets doen, en zou de pakketzoeker met
    een droogte-eis het verkeerde antwoord geven.

    """
    without = simulate_deficit(_state_with_supply(0.0), Deficit(4.0, 30))
    with_rise = simulate_deficit(
        _state_with_supply(0.0, target_level_rise_m=0.20), Deficit(4.0, 30)
    )

    # 0,20 m over 3,5 % open water is 7,0 mm over de polder
    assert with_rise.buffer_mm - without.buffer_mm == pytest.approx(
        0.20 * 0.035 * 1000, abs=1e-9
    )
    assert without.shortfall_mm - with_rise.shortfall_mm == pytest.approx(
        0.20 * 0.035 * 1000, abs=1e-9
    )
    # en de bodem komt later in zicht in plaats van meteen
    assert without.days_until_buffer_empty == 0.0
    assert with_rise.days_until_buffer_empty > 1.0


def test_the_two_drought_readings_measure_the_same_water():
    """De statische en de dynamische voorraad-uitlezing zijn één ding, niet twee.

    `PolderState.retained_volume_mm` is de peil-uitspraak: de inhoud van de band onder het
    opgezette streefpeil. `DeficitResult.buffer_mm` is de waterstand-uitspraak: wat er in een
    droge periode werkelijk uit die band komt. Zakt de reeks tot de bodem, dan moeten die
    twee exact hetzelfde getal zijn - anders beschrijven twee formules op twee velden
    hetzelfde water.
    """
    for rise in (0.10, 0.20, 0.50):
        state = _state_with_supply(0.0, target_level_rise_m=rise)
        result = simulate_deficit(state, Deficit(4.0, 30))
        assert result.buffer_mm == pytest.approx(state.retained_volume_mm, abs=1e-9)


def test_the_drought_buffer_is_the_whole_level_band():
    """Marge en opzet tellen allebei mee, en ze zijn onderling uitwisselbaar in diepte.

    De band is `[-level_margin_m, +target_level_rise_m]` rond het oorspronkelijke peil; wat
    de droogte kan opeten is de hele hoogte daarvan. Dertig centimeter marge en dertig
    centimeter opzet geven dus dezelfde bufferdiepte, ook al zijn het verschillende dingen -
    de een is bedrijfsvoering, de ander een staande peilkeuze.
    """
    margin_only = simulate_deficit(
        _state_with_supply(0.0, level_margin_m=0.30), Deficit(4.0, 30)
    )
    rise_only = simulate_deficit(
        _state_with_supply(0.0, target_level_rise_m=0.30), Deficit(4.0, 30)
    )
    both = simulate_deficit(
        _state_with_supply(0.0, level_margin_m=0.15, target_level_rise_m=0.15),
        Deficit(4.0, 30),
    )

    assert margin_only.shortfall_mm == pytest.approx(rise_only.shortfall_mm, abs=1e-9)
    assert both.shortfall_mm == pytest.approx(rise_only.shortfall_mm, abs=1e-9)


def test_the_supply_tools_keep_their_answer():
    """De aanvoertools zetten geen peilopzet, dus voor hen verandert er niets.

    De bufferdiepte-wijziging raakt alleen toestanden mét opzet. `_state` in `supply.py`
    vult uitsluitend `level_margin_m` uit `drawdown_available_m`, dus de bestaande ankers
    blijven staan. Dit is de test die dat expliciet maakt in
    plaats van het te hopen.

    Dat de aanvoerkant geen peilopzet zet is inmiddels geen toevalligheid meer maar een
    keuze met een reden: `drawdown_available_m` IS de hele band, dus opzet er apart bij
    optellen zou dubbeltellen. Zie
    `test_supply.py::test_the_available_drawdown_is_the_whole_level_band`.
    """
    state = _state_with_supply(0.0, level_margin_m=0.30)
    assert state.target_level_rise_m == 0.0
    result = simulate_deficit(state, Deficit(4.0, 30))
    assert result.shortfall_mm == pytest.approx(109.5, abs=1e-6)


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
    """Een tekort is een vraag en geen negatieve afvoer.

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


# --- de bron is eindig -----------------------------------------------------


def _dry_polder():
    """Twente-achtig: 4000 ha met 1 % open water, dus bijna geen eigen berging."""
    return PolderState(
        area_ha=4000,
        pct_open_water=1.0,
        level_margin_m=0.3,
        connections=(Connection(capacity_in_m3_per_sec=1.81),),
    )


def test_an_unlimited_source_is_the_behaviour_that_was_always_there():
    """De default verandert niets; dat is de eis van elke generalisatie in dit project."""
    state = _dry_polder()
    without = simulate_deficit(state, Deficit(4.0, 30))
    explicit = simulate_deficit(
        state, Deficit(4.0, 30), BoundaryCondition(float("inf"))
    )

    assert without.shortfall_mm == pytest.approx(explicit.shortfall_mm, abs=1e-12)
    assert without.supplied_mm == pytest.approx(explicit.supplied_mm, abs=1e-12)
    assert not without.source_ran_dry
    assert without.days_until_source_empty == float("inf")


def test_the_volume_the_inlet_needs_is_reported():
    """Het Twente-anker: 1,81 m3/s over 30 dagen is 4,7 miljoen m3.

    Een debiet klinkt haalbaar en een volume nodigt uit tot narekenen. Het is ook de
    grootheid waarin de bron eindig is, dus het is de eenheid waarin de vraag en het aanbod
    op elkaar te leggen zijn.
    """
    result = simulate_deficit(_dry_polder(), Deficit(4.0, 30))
    assert result.source_volume_used_m3 == pytest.approx(1.81 * 30 * 86_400, rel=1e-9)


def test_an_empty_source_is_a_shortfall_and_not_a_covered_answer():
    """Zonder water is het tekort het hele volume, niet "0,45 l/s/ha en je bent gedekt".

    Dit is het punt waar de caveat over aanvoerbeschikbaarheid over gaat, nu als getal.
    """
    state = _dry_polder()
    covered = simulate_deficit(state, Deficit(4.0, 30))
    dry = simulate_deficit(state, Deficit(4.0, 30), BoundaryCondition(0.0))

    assert covered.shortfall_mm < 1.0  # met water gaat het bijna helemaal goed
    assert dry.source_volume_used_m3 == pytest.approx(0.0)
    assert dry.days_until_source_empty == pytest.approx(0.0)
    # het tekort is de hele vraag min de eigen berging, en die is hier klein
    assert dry.shortfall_mm > 0.9 * dry.demand_mm


def test_a_source_that_runs_dry_halfway_says_when():
    """De spiegel van `days_until_buffer_empty`: de bron bepaalt of er iets te kopen is."""
    state = _dry_polder()
    full_need = simulate_deficit(state, Deficit(4.0, 30)).source_volume_used_m3
    half = simulate_deficit(state, Deficit(4.0, 30), BoundaryCondition(0.5 * full_need))

    assert half.days_until_source_empty == pytest.approx(15, abs=1.0)
    assert half.source_volume_used_m3 == pytest.approx(0.5 * full_need, rel=1e-6)
    assert half.shortfall_mm > 0.0


def test_a_second_pass_changes_nothing():
    """Waarom een pass genoeg is, als uitvoerbare bewering in plaats van een comment.

    De bronbeperking is inactief zolang er voorraad is, dus de reeks tot het afknijpmoment is
    dezelfde als zonder beperking. Wat erna gebeurt - de waterstand zakt door, de inlaat zou meer
    willen - kan het verbruik ervoor niet meer veranderen. Causaliteit, geen vast punt.

    De toets: neem het verbruik uit de doorrekening MET de eindige bron en gebruik dat als
    nieuwe bronvoorraad. Klopt het argument, dan komt er hetzelfde uit; klopt het niet, dan
    schuift het afknijpmoment en is dit een iteratie die we niet hebben gedraaid.
    """
    state = _dry_polder()
    full_need = simulate_deficit(state, Deficit(4.0, 30)).source_volume_used_m3
    first = simulate_deficit(
        state, Deficit(4.0, 30), BoundaryCondition(0.4 * full_need)
    )
    second = simulate_deficit(
        state, Deficit(4.0, 30), BoundaryCondition(first.source_volume_used_m3)
    )

    assert second.days_until_source_empty == pytest.approx(
        first.days_until_source_empty, abs=1 / 24
    )
    assert second.shortfall_mm == pytest.approx(first.shortfall_mm, rel=1e-9)
    assert second.supplied_mm == pytest.approx(first.supplied_mm, rel=1e-9)


def test_the_mass_balance_still_closes_with_a_finite_source():
    """Vraag = geleverd + berging + tekort, ook als de bron halverwege opdroogt."""
    state = _dry_polder()
    full_need = simulate_deficit(state, Deficit(4.0, 30)).source_volume_used_m3
    for fraction in (0.0, 0.25, 0.6, 1.0, 2.0):
        result = simulate_deficit(
            state, Deficit(4.0, 30), BoundaryCondition(fraction * full_need)
        )
        assert (
            result.supplied_mm + result.buffer_mm + result.shortfall_mm
            == pytest.approx(result.demand_mm, rel=1e-9)
        )


def test_a_finite_source_can_make_the_inverse_infeasible():
    """En dat is het eerlijke antwoord in plaats van een capaciteit die niets oplevert.

    `solve_supply` zoekt de kleinste inlaat die het tekort dekt. Met een lege bron dekt geen
    enkele inlaat iets - meer capaciteit haalt het water niet uit een droge boezem - dus is
    de status `ACTION_INFEASIBLE` en niet `EXACT`. De monotonie waar de bisectie op rust
    blijft gelden: het tekort daalt met de capaciteit en vlakt af op wat de bron toelaat.

    De toestand gaat er zonder inlaat in, want dat is de precondititie van `solve_supply`:
    hij rekent de gevraagde capaciteit als DELTA op wat er al is, en die delta mag niet
    negatief zijn. Zo roept `calculate_supply_given_h` hem ook aan.
    """
    state = PolderState(
        area_ha=4000,
        pct_open_water=1.0,
        level_margin_m=0.3,
        connections=(Connection(capacity_in_m3_per_sec=0.0),),
    )
    with_water = solve_supply(state, Deficit(4.0, 30))
    assert with_water.status is SolveStatus.EXACT

    without = solve_supply(state, Deficit(4.0, 30), boundary=BoundaryCondition(0.0))
    assert without.status is SolveStatus.ACTION_INFEASIBLE
    assert without.shortfall_mm > 0.9 * without.demand_mm


@pytest.mark.parametrize("depth_m", [0.0, 1e-17, 1e-13, 1e-12, 1e-9])
def test_a_buffer_that_is_barely_there_is_still_a_number(depth_m):
    """Een bufferdiepte van 1e-17 komt de pakketzoeker op zijn zoekpad tegen.

    En dan liep de interpolatie in `_crossing_day` op een deling door nul. De oorzaak was
    dat "ligt de stand op de bodem" op twee plekken met een ANDERE marge werd beantwoord:
    `on_the_floor` met een marge van 1e-12 en de interpolatie met een exacte vergelijking.
    Bij een diepte van 1e-17 zei de eerste dat de bodem geraakt was en de tweede dat er nog
    buffer over was, en dan interpoleert de code tussen twee standen die allebei nul zijn.

    De inlaat moet de vraag DEKKEN, anders zakt de stand meteen weg en is het verschil
    tussen de twee standen niet nul meer. Dat is precies de stand van zaken waarin de
    zoeker deze waarden langskomt: hij zoekt een pakket dat de eis haalt, en beweegt de
    peilband daarbij door nul heen.

    Op CI viel dit in drie SLSQP-tests om en lokaal niet - de zoeker komt zo'n waarde alleen
    langs als zijn pad er toevallig langs loopt. Vandaar dat het hier als eigenschap staat
    en niet als de ene casus die toevallig omviel.
    """
    covered = _state_with_supply(4.0, level_margin_m=depth_m)
    result = simulate_deficit(covered, Deficit(4.0, 30))

    assert result.shortfall_mm == 0.0
    assert result.days_until_buffer_empty >= 0.0
