"""Een netwerk van polders: dezelfde kern, nu met de koppeling erin.

De belangrijkste test is de eerste: één knoop plus de rand moet bitgelijk zijn aan
`simulate`. Zolang dat waar is, is het netwerk een generalisatie en geen tweede rekenpad, en
is de gouden regressie tegen het rekenblad ook een test op het netwerk.

Twee tests dekken fouten die tijdens het ontwerp bijna zijn gemaakt en die op een ketting
niet opvallen: dat de aanvoer wordt opgeteld in plaats van toegewezen, en dat de
laagindeling de langste en niet de kortste pad-afstand is.
"""

import time

import numpy as np
import pytest

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.system import (
    BOUNDARY,
    SystemState,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.network import (
    bracket_network,
    node_forcing,
    simulate_network,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

SECONDS_PER_HOUR = 3600
SQUARE_METRES_PER_HECTARE = 1e4
TOLERANCE_M = 1e-12

REFERENCE_STORM = {
    "return_period": 1000,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
    "rainfall_regime": "R",
}
POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}


@pytest.fixture
def storm():
    return StoreInputGivenH(**REFERENCE_STORM, **POLDER, delta_h_available=1.0)


def _polder(to=OUTSIDE, capacity=5.0, area_ha=4000.0, head_max=None, **overrides):
    return PolderState(
        area_ha=area_ha,
        pct_open_water=3.5,
        connections=(
            Connection(to=to, capacity_out_m3_per_sec=capacity, head_max_m=head_max),
        ),
        **overrides,
    )


def _chain(length, capacity=5.0, head_max=None):
    """Kralenketting: elke polder loost op de volgende, de laatste op de rand."""
    names = [f"n{index}" for index in range(length)]
    polders = [
        _polder(
            to=OUTSIDE if index == length - 1 else names[index + 1],
            capacity=capacity,
            head_max=head_max,
        )
        for index in range(length)
    ]
    return SystemState.from_polders(polders, names=names)


# --- het netwerk met een knoop is het poldermodel -----------------------------------


def test_a_single_node_equals_the_polder_model(storm):
    """De ankertest van WP10: bitgelijk, niet ongeveer.

    Zolang dit klopt is de gouden regressie tegen `TttE_v03.xlsx` ook een test op het
    netwerk, want de eenpolder-casus is de kleinste instantie van het algemene geval.
    """
    polder = _polder()
    solo = simulate(polder, storm)
    network = simulate_network(SystemState.from_polders([polder], names=["A"]), storm)

    assert network.depth == 1
    assert network.dh_max_m[0] == pytest.approx(solo.dh_max_m, abs=TOLERANCE_M)
    assert network.converged


def test_the_boundary_node_is_not_a_row_in_the_arrays():
    system = SystemState.from_polders([_polder()], names=["A"])
    assert system.size == 1
    assert system.downstream[0] == BOUNDARY


def test_the_projection_back_to_polders_round_trips():
    original = [_polder(to="B", capacity=3.0), _polder(capacity=7.0)]
    system = SystemState.from_polders(original, names=["A", "B"])
    assert system.to_polders() == tuple(original)


# --- de topologie ------------------------------------------------------------------


def test_depth_is_the_longest_path_and_not_the_shortest():
    """A -> C, B -> C, A -> D, D -> C.

    Met kortste-pad-diepte komt C op diepte 1 te staan, samen met D - en dan wordt C
    gerekend terwijl D, die water in C loost, nog niet klaar is. De invariant die de hele
    pass-structuur draagt is dat elke voorganger strikt lager ligt, en alleen
    langste-pad-indeling levert die.

    Fan-out is een per knoop, dus A -> C en A -> D kan niet in een graaf; hier gaat A via D
    naar C en loost B rechtstreeks op C. Dat is dezelfde diamant voor het punt dat hij maakt.
    """
    system = SystemState.from_polders(
        [_polder(to="D"), _polder(to="C"), _polder(), _polder(to="C")],
        names=["A", "B", "C", "D"],
    )
    levels = system.topological_levels()
    depth_of = {
        system.names[node]: index
        for index, group in enumerate(levels)
        for node in group
    }
    assert depth_of == {"A": 0, "B": 0, "D": 1, "C": 2}

    # de invariant zelf, en niet alleen de uitkomst
    for upstream, down in enumerate(system.downstream):
        if down != BOUNDARY:
            assert depth_of[system.names[upstream]] < depth_of[system.names[down]]


def test_a_cycle_is_rejected():
    with pytest.raises(ValueError, match="cyclus"):
        SystemState.from_polders([_polder(to="B"), _polder(to="A")], names=["A", "B"])


def test_an_unknown_destination_is_rejected():
    with pytest.raises(ValueError, match="bestaat niet"):
        SystemState.from_polders([_polder(to="nergens")], names=["A"])


def test_more_than_one_outgoing_connection_is_rejected():
    """Fan-out vraagt een verdeling over de twee kanten, en dat is WP11."""
    two_pumps = PolderState(
        area_ha=4000,
        pct_open_water=3.5,
        connections=(
            Connection(to="B", capacity_out_m3_per_sec=3.0),
            Connection(to=OUTSIDE, capacity_out_m3_per_sec=2.0),
        ),
    )
    with pytest.raises(ValueError, match="uitgaande"):
        SystemState.from_polders([two_pumps, _polder()], names=["A", "B"])


# --- de koppeling zelf --------------------------------------------------------------


def test_without_derating_one_pass_per_depth_is_exact(storm):
    """Een ketting van vier, tegen knoop-voor-knoop met de aanvoer doorgegeven.

    Zonder terugkoppeling is er niets te itereren: de pass in topologische orde is het
    antwoord. Dat is niet alleen sneller maar een ander soort antwoord - geen tolerantie,
    geen convergentievraag.
    """
    system = _chain(4)
    network = simulate_network(system, storm)
    assert network.iterations == 0
    assert network.depth == 4

    inflow = None
    for index in range(4):
        step = simulate(_polder(), storm, inflow_m3_per_sec=inflow)
        assert network.dh_max_m[index] == pytest.approx(step.dh_max_m, abs=TOLERANCE_M)
        inflow = step.pumped_m3_per_sec


def test_fan_in_sums_the_upstream_exchange(storm):
    """Twee polders op dezelfde knoop: de aanvoer is de som, niet de laatste.

    Met een toewijzing in plaats van een scatter-add overschrijft de tweede bovenstroomse
    polder de eerste. Dat valt op een ketting niet op en is op elke andere graaf stil
    verkeerd.
    """
    system = SystemState.from_polders(
        [_polder(to="C"), _polder(to="C"), _polder(area_ha=8000.0)],
        names=["A", "B", "C"],
    )
    network = simulate_network(system, storm)

    receiving = system.names.index("C")
    upstream = [system.names.index("A"), system.names.index("B")]
    expected = network.exchange_m3_per_sec[upstream].sum(axis=0)
    assert np.abs(network.inflow_m3_per_sec[receiving] - expected).max() < TOLERANCE_M
    # en de twee bovenstroomse polders dragen echt allebei bij
    assert (
        network.inflow_m3_per_sec[receiving].max()
        > network.exchange_m3_per_sec[upstream[0]].max()
    )


def test_coupling_raises_the_downstream_peak(storm):
    """De uitspraak waar de cascade om begonnen is: afvoeren wentelt af."""
    isolated = simulate(_polder(area_ha=8000.0), storm).dh_max_m
    system = SystemState.from_polders(
        [_polder(to="C"), _polder(to="C"), _polder(area_ha=8000.0)],
        names=["A", "B", "C"],
    )
    coupled = simulate_network(system, storm).dh_max_m[2]
    assert coupled > isolated


def test_derating_shifts_the_burden_upstream(storm):
    """Kopafhankelijke capaciteit verplaatst de last; hij verergert hem niet overal.

    Op een ketting van vijf, vrije afstroming tegen derating vanaf 1,5 m:

        vrij     1,81  3,59  3,69  3,69  3,69
        derated  3,18  3,63  3,69  3,69  2,27

    De bovenste polder gaat van 1,81 naar 3,18 m omdat zijn gemaal wordt geblokkeerd door
    de stand van zijn buur. De onderste gaat van 3,69 naar 2,27 m, want er komt minder
    water aan. Twee effecten in tegengestelde richting - meer aanvoer verhoogt de stand,
    meer eigen capaciteit verlaagt hem - en juist daarom is "derating maakt alles erger"
    onwaar en is de klem in `bracket_network` gemengd.

    **Welke van de twee is nu het afwentelen?** De vrije afstroming. Afwentelen is je
    probleem naar benedenstrooms schuiven, en dat is precies wat de bovenste polder in de
    eerste rij doet: hij houdt 1,81 m over terwijl de onderste 3,69 m krijgt. Derating is
    het omgekeerde - de benedenstroomse volle boezem duwt terug, en dan houdt bovenstrooms
    het water zelf vast. Dat is niet afwenteling maar het fysieke mechanisme waar het
    niet-afwentelen-principe de beleidsregel van is.

    En daarmee staat het bedrag erbij. Wat de bovenste polder exporteerde is 1,38 m
    peilstijging; wat de onderste eraan overhield 1,42 m. Dat is de externaliteit, gemeten
    in plaats van per decreet geinternaliseerd. Zonder de koppeling in het model kan de
    kostenafweging hem niet zien, en dan is afvoeren goedkoop om de verkeerde reden - zie
    PLAN_TOOLS_REFACTOR.md Sec. 8.3.
    """
    free = simulate_network(_chain(5), storm)
    derated = simulate_network(_chain(5, head_max=1.5), storm)

    assert free.iterations == 0
    assert derated.iterations > 0
    assert derated.converged

    # bovenstrooms: het gemaal levert minder en de stand loopt op
    assert derated.exchange_m3_per_sec[0].sum() < free.exchange_m3_per_sec[0].sum()
    assert derated.dh_max_m[0] > free.dh_max_m[0]
    # benedenstrooms: minder aanvoer, dus een lagere piek
    assert derated.dh_max_m[-1] < free.dh_max_m[-1]

    # En het systeem als geheel houdt niet MEER water vast: het houdt hetzelfde water op
    # een andere plek. Het benedenstroomse gemaal is hier de bottleneck en draait in beide
    # gevallen voluit, dus er verlaat evenveel water het systeem. Verplaatsen en niet
    # verergeren - precies wat de gemengde klem in `bracket_network` nodig maakt.
    assert derated.water_level_m[:, -1].sum() == pytest.approx(
        free.water_level_m[:, -1].sum(), rel=1e-12
    )
    assert derated.water_level_m[0, -1] > free.water_level_m[0, -1]
    assert derated.water_level_m[-1, -1] < free.water_level_m[-1, -1]


def test_the_bracket_contains_the_iterated_answer(storm):
    """De klem geldt altijd, ook als de iteratie niet convergeert.

    Ondergrens: geen aanvoer, eigen gemaal voluit. Bovengrens: de aanvoer van vrije
    afstroming en het eigen gemaal uit. Beide in een scan, zonder iteratie.
    """
    system = _chain(5, head_max=1.5)
    lowest, highest = bracket_network(system, storm)
    answer = simulate_network(system, storm).dh_max_m

    assert (lowest <= answer + TOLERANCE_M).all()
    assert (answer <= highest + TOLERANCE_M).all()
    assert (lowest < highest).all()


def test_not_converged_is_reported_and_not_silently_returned(storm):
    """Een tussenliggende iteratie is optimistisch over de afvoer en dus onveilig."""
    result = simulate_network(_chain(5, head_max=1.5), storm, max_iterations=1)
    assert not result.converged
    with pytest.raises(ValueError, match="niet geconvergeerd"):
        result.require_converged()


# --- massabalans en schaal ----------------------------------------------------------


def test_the_mass_balance_closes_over_the_network(storm):
    """Wat er valt gaat het systeem uit of staat er nog in. Interne uitwisseling valt weg."""
    system = SystemState.from_polders(
        [_polder(to="C"), _polder(to="C"), _polder(area_ha=8000.0)],
        names=["A", "B", "C"],
    )
    result = simulate_network(system, storm)
    runoff, direct = node_forcing(system, storm)
    area_open_water_m2 = system.area_open_water_ha * SQUARE_METRES_PER_HECTARE

    entered_m3 = runoff.sum() * SECONDS_PER_HOUR + float(
        (direct.sum(axis=1) * area_open_water_m2).sum()
    )
    left_m3 = (
        result.exchange_m3_per_sec[system.downstream == BOUNDARY].sum()
        * SECONDS_PER_HOUR
    )
    stored_m3 = float((result.water_level_m[:, -1] * area_open_water_m2).sum())

    assert left_m3 + stored_m3 == pytest.approx(entered_m3, rel=1e-9)


def test_national_scale_stays_within_budget(storm):
    """8500 knopen in twee lagen, onder 100 ms.

    De vectorisatie zit in de breedte: de 8499 polders van laag 0 gaan in een scan. Het
    aantal passes is de diepte - hier 2 - en niet het aantal knopen. Voor Nederland is die
    diepte 3 a 4 tegen een breedte van duizenden, en dat is de hele reden dat dit schaalt.
    """
    count = 8499
    names = [f"p{index}" for index in range(count)] + ["boezem"]
    polders = [_polder(to="boezem", area_ha=400.0) for _ in range(count)]
    polders.append(_polder(area_ha=400.0 * count, capacity=5.0 * count))
    system = SystemState.from_polders(polders, names=names)

    simulate_network(system, storm)  # warm, zodat de bui gecached is
    start = time.perf_counter()
    result = simulate_network(system, storm)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.depth == 2
    assert elapsed_ms < 100, f"{elapsed_ms:.1f} ms voor {system.size} knopen"


def test_the_scan_is_shared_so_identical_nodes_give_identical_answers(storm):
    """Vectorisatie over de breedte mag geen knoop-afhankelijk gedrag introduceren."""
    system = SystemState.from_polders(
        [_polder(area_ha=1000.0) for _ in range(6)],
        names=[f"n{index}" for index in range(6)],
    )
    result = simulate_network(system, storm)
    assert np.ptp(result.dh_max_m) < TOLERANCE_M
