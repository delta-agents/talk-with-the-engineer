"""De verdringingsreeks op een boom: gesloten vorm, en waarom dat mag.

Twee soorten test staan hier naast elkaar, en dat is bewust. De eerste soort zijn ankers op
papier: een speelgoednet van drie afnemers waar je de uitkomst met de hand narekent. De
tweede is een vergelijking met een echte LP-solver over honderden willekeurige netten - want
de bewering "hier hoeft geen LP in" is een wiskundige claim en die hoort getoetst, niet
beweerd.

En er staat één test die de GRENS vastlegt. De gesloten vorm werkt doordat elke afnemer
precies één pad naar zijn bron heeft; met twee bronnen is greedy aantoonbaar suboptimaal.
Zolang `SystemState` fan-out 1 afdwingt zitten we aan de goede kant, en die test zegt wat er
gebeurt als dat verandert.
"""

import numpy as np
import pytest
from scipy.optimize import linprog

from talk_with_the_engineer.core.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.core.results import MeasureRole
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.system import SystemState
from talk_with_the_engineer.core.allocation import (
    WithinShellRule,
    allocate,
    theta_breakpoints,
    theta_table,
)

DAYS = 30
SECONDS = DAYS * 86_400.0
MILLION = 1e6


def _node(intake_m3_per_sec: float, drains_to: str | None = None) -> PolderState:
    """Een knoop met een inlaat; de natte kant doet in deze tests niet mee."""
    return PolderState(
        area_ha=4000,
        pct_open_water=3.5,
        connections=(
            Connection(
                to=drains_to or OUTSIDE,
                capacity_out_m3_per_sec=5.0,
                capacity_in_m3_per_sec=intake_m3_per_sec,
            ),
        ),
    )


@pytest.fixture
def three_consumers() -> SystemState:
    """Drie afnemers op één boezem, de boezem op de buitenwereld.

    De boezem heeft zelf geen vraag: hij is transport. Dat is precies het geval waarin een
    ketting geen ketting is maar een gedeelde pot - de drie afnemers staan naast elkaar.
    """
    return SystemState.from_polders(
        [
            _node(1.0, "boezem"),
            _node(1.0, "boezem"),
            _node(1.0, "boezem"),
            _node(10.0),
        ],
        names=["drinkwater", "industrie", "landbouw", "boezem"],
    )


# demand en categorie per knoop, in de volgorde van `three_consumers`
DEMAND = np.array([1.0, 2.0, 3.0, 0.0]) * MILLION
CATEGORIES = np.array([2, 3, 4, 4])


# --- ankers op papier ----------------------------------------------------------------


def test_the_legal_order_starves_the_lowest_category_first(three_consumers):
    """4 miljoen m3 over een vraag van 6: categorie 4 draagt het hele tekort.

    Op papier: categorie 2 vraagt 1 en krijgt 1, categorie 3 vraagt 2 en krijgt 2, en voor
    categorie 4 is er 1 van de 3 over. Dat is de verdringingsreeks, en het is geen weging -
    het is een ordening waar geen gewicht tegenop kan.
    """
    result = allocate(three_consumers, DEMAND, CATEGORIES, 4 * MILLION, DAYS)

    assert result.coverage_of_category(2) == pytest.approx(1.0)
    assert result.coverage_of_category(3) == pytest.approx(1.0)
    assert result.coverage_of_category(4) == pytest.approx(1 / 3)
    assert result.binding_category == 4
    assert result.granted_m3.sum() == pytest.approx(4 * MILLION)


def test_the_roles_are_the_same_vocabulary_as_the_package_search(three_consumers):
    """`FORCED` / `OPTIONAL` / `ABSENT`, dezelfde drie woorden als bij het maatregelgebied."""
    result = allocate(three_consumers, DEMAND, CATEGORIES, 4 * MILLION, DAYS)

    assert result.role_of(2) is MeasureRole.FORCED
    assert result.role_of(3) is MeasureRole.FORCED
    assert result.role_of(4) is MeasureRole.OPTIONAL

    dry = allocate(three_consumers, DEMAND, CATEGORIES, 1 * MILLION, DAYS)
    assert dry.role_of(2) is MeasureRole.FORCED
    assert dry.role_of(3) is MeasureRole.ABSENT
    assert dry.role_of(4) is MeasureRole.ABSENT


def test_equal_deficit_within_one_shell(three_consumers):
    """Binnen één categorie krijgt iedereen dezelfde dekkingsfractie.

    Dit is de PROXY en niet het wettelijke criterium: art. 3.14 Bkl noemt binnen categorie 3
    en 4 minimalisatie van de economische maatschappelijke schade, en dat is de gewogen vorm.
    Gelijk tekort is wat je doet als je de schadefuncties niet kent - en wij kennen ze niet.
    """
    same_shell = np.array([4, 4, 4, 4])
    result = allocate(three_consumers, DEMAND, same_shell, 3 * MILLION, DAYS)

    coverage = result.coverage[:3]
    assert coverage == pytest.approx([0.5, 0.5, 0.5])


def test_an_intake_that_binds_caps_what_a_consumer_can_take(three_consumers):
    """De eigen inlaat is een grens, ook als er genoeg water is.

    Landbouw vraagt 3 miljoen m3 maar heeft 1 m3/s inlaat, en dat is over 30 dagen
    2,592 miljoen. Meer water in de boezem verandert daar niets aan - dat is het verschil
    tussen beschikbaarheid en capaciteit, en het is de reden dat de eigen inlaat een
    aparte klem is en niet in de bronbeperking opgaat.
    """
    result = allocate(three_consumers, DEMAND, CATEGORIES, 100 * MILLION, DAYS)

    assert result.granted_m3[2] == pytest.approx(1.0 * SECONDS)
    assert result.shortfall_m3[2] == pytest.approx(3 * MILLION - 1.0 * SECONDS)
    # de twee kleinere vragen passen wel binnen hun inlaat
    assert result.coverage_of_category(2) == pytest.approx(1.0)
    assert result.coverage_of_category(3) == pytest.approx(1.0)


def test_a_shared_boezem_intake_binds_for_everyone(three_consumers):
    """De boezem is zelf een inlaat, en die klemt de som van wat erachter hangt.

    Dat is het structurele verschil met de natte kant: daar is de beperking lokaal per kant,
    hier deelt iedereen achter de boezem één keel.
    """
    narrow = SystemState.from_polders(
        [
            _node(1.0, "boezem"),
            _node(1.0, "boezem"),
            _node(1.0, "boezem"),
            _node(0.5),  # de boezem laat over 30 dagen maar 1,296 mln m3 door
        ],
        names=["drinkwater", "industrie", "landbouw", "boezem"],
    )
    result = allocate(narrow, DEMAND, CATEGORIES, 100 * MILLION, DAYS)

    assert result.granted_m3.sum() == pytest.approx(0.5 * SECONDS)
    # en de reeks geldt binnen die keel: categorie 2 eerst
    assert result.coverage_of_category(2) == pytest.approx(1.0)
    assert result.granted_m3[2] == pytest.approx(0.0, abs=1.0)


def test_an_infinite_source_covers_everything_within_capacity(three_consumers):
    """Met een oneindige bron is de inlaat de enige grens; dat is het huidige gedrag."""
    result = allocate(three_consumers, DEMAND, CATEGORIES, float("inf"), DAYS)
    within_capacity = np.minimum(
        DEMAND, three_consumers.capacity_in_m3_per_sec * SECONDS
    )
    assert result.granted_m3 == pytest.approx(within_capacity)
    assert result.binding_category == 4  # landbouw loopt tegen zijn eigen inlaat


def test_nothing_available_is_a_shortfall_and_not_a_covered_answer(three_consumers):
    """Het Twente-punt: zonder water is het tekort het hele volume.

    De aanvoertool zei "0,45 l/s/ha en je tekort is gedekt" omdat hij aannam dat het water
    bij de inlaat is. Met een eindige bron is dat geen aanname meer maar een getal.
    """
    result = allocate(three_consumers, DEMAND, CATEGORIES, 0.0, DAYS)

    assert result.granted_m3.sum() == pytest.approx(0.0)
    assert result.shortfall_m3.sum() == pytest.approx(DEMAND.sum())
    assert result.binding_category == 2


def test_mass_is_conserved_and_never_exceeds_the_source(three_consumers):
    """Niemand krijgt meer dan er is, en niemand krijgt meer dan hij vroeg."""
    for available in (0.0, 1e5, 2.5 * MILLION, 6 * MILLION, 50 * MILLION):
        result = allocate(three_consumers, DEMAND, CATEGORIES, available, DAYS)
        assert result.granted_m3.sum() <= available + 1e-6
        assert np.all(result.granted_m3 <= DEMAND + 1e-9)
        assert np.all(result.granted_m3 >= -1e-12)


# --- de gesloten vorm tegen een echte LP ---------------------------------------------


def _random_two_level_system(rng):
    """Een willekeurige boom: afnemers op een handvol boezems, boezems op de buitenwereld."""
    branches = int(rng.integers(1, 4))
    consumers = int(rng.integers(2, 8))
    parents = rng.integers(0, branches, consumers)
    names = [f"c{i}" for i in range(consumers)] + [f"b{j}" for j in range(branches)]
    polders = [
        _node(float(rng.uniform(0.05, 2.0)), f"b{parents[i]}") for i in range(consumers)
    ]
    polders += [_node(float(rng.uniform(0.2, 4.0))) for _ in range(branches)]
    system = SystemState.from_polders(polders, names=names)

    demand = np.concatenate(
        [rng.uniform(0.1, 4.0, consumers) * MILLION, np.zeros(branches)]
    )
    categories = np.concatenate([rng.integers(1, 5, consumers), np.full(branches, 4)])
    total = float(np.minimum(demand, system.capacity_in_m3_per_sec * SECONDS).sum())
    return system, demand, categories, float(rng.uniform(0.0, total))


def _downstream_of(downstream, node) -> list[int]:
    """De knoop en alle knopen benedenstrooms ervan, tot aan de uitlaat (-1)."""
    if node == -1:
        return []
    return [node] + _downstream_of(downstream, int(downstream[node]))


def _lp_category_totals(system, demand, categories, available):
    """Wat een lexicografische reeks LP's per categorie maximaal toewijst.

    Dit is de WEAP- en Ribasim-vorm: optimaliseer categorie 1, zet het bereikte niveau vast
    als constraint, ga door met 2. Precies de lus die we niet willen draaien - hier alleen
    als onafhankelijke referentie.
    """
    size = system.size
    capacity = system.capacity_in_m3_per_sec.astype(float) * SECONDS
    # elke knoop draagt zichzelf en al zijn nakomelingen door zijn eigen inlaat
    through = np.zeros((size, size))
    for node in range(size):
        through[_downstream_of(system.downstream, node), node] = 1.0
    rows = [through[node] for node in range(size)]
    bounds_high = np.minimum(demand, capacity)

    A_ub = [np.ones(size)] + rows
    b_ub = [available] + [capacity[node] for node in range(size)]
    totals = {}
    for category in sorted(set(int(c) for c in categories)):
        selection = categories == category
        if demand[selection].sum() <= 0:
            continue
        objective = np.where(selection, -1.0, 0.0)
        solution = linprog(
            objective,
            A_ub=np.array(A_ub),
            b_ub=np.array(b_ub),
            bounds=[(0.0, float(high)) for high in bounds_high],
            method="highs",
        )
        assert solution.success, solution.message
        totals[category] = -solution.fun
        row = np.where(selection, -1.0, 0.0)
        A_ub.append(row)
        b_ub.append(-totals[category] + 1e-6)
    return totals


def test_the_closed_form_matches_a_reference_lp():
    """De kern van de claim: geen LP nodig, en dat is te toetsen.

    Per categorie het toegewezen TOTAAL, want dat is wat de lexicografische ordening
    vastlegt; hoe het binnen een categorie wordt verdeeld is de tweede keuze en die legt de
    LP niet vast. Zie `WithinShellRule`.

    Vaste seed, want een test die soms faalt is geen test.
    """
    rng = np.random.default_rng(20260823)
    worst = 0.0
    compared = 0
    for _ in range(60):
        system, demand, categories, available = _random_two_level_system(rng)
        result = allocate(system, demand, categories, available, DAYS)
        for category, expected in _lp_category_totals(
            system, demand, categories, available
        ).items():
            got = result.granted_m3[categories == category].sum()
            # relatief aan de VRAAG van de categorie en niet aan het toegewezen totaal: bij
            # een categorie die (bijna) niets krijgt is dat laatste nul, en dan meet je de
            # eigen slack van de referentie-LP in plaats van een afwijking
            scale = max(float(demand[categories == category].sum()), 1.0)
            worst = max(worst, abs(got - expected) / scale)
            compared += 1
    assert compared > 100, "te weinig vergelijkingen om iets te zeggen"
    # gemeten over 300 netten en 823 vergelijkingen: 6,9e-12, dus machineprecisie. De
    # gesloten vorm IS het LP-optimum en benadert het niet - vandaar deze drempel en
    # niet een ruime.
    assert worst < 1e-9, f"grootste relatieve afwijking {worst:.2e}"


def test_the_result_is_identical_across_repeated_runs(three_consumers):
    """Geen solver in het pad betekent geen platformverschil - invariant I6.

    Deze test kan geen tweede besturingssysteem starten, dus hij toetst wat hij kan: het
    antwoord is bit-identiek over herhaalde aanroepen en hangt niet van een startpunt of
    een iteratieorde af. Dat is bij een sort en een cumsum een eigenschap; bij een
    LP-solver zou het een hoop zijn.
    """
    first = allocate(three_consumers, DEMAND, CATEGORIES, 4 * MILLION, DAYS)
    for _ in range(5):
        again = allocate(three_consumers, DEMAND, CATEGORIES, 4 * MILLION, DAYS)
        assert np.array_equal(first.granted_m3, again.granted_m3)


# --- waar de gesloten vorm ophoudt ---------------------------------------------------


def test_two_sources_would_break_the_greedy_and_that_is_the_boundary():
    """Fan-out 2 kost de gesloten vorm, en dit is het tegenvoorbeeld.

    Twee bronnen met elk 1 eenheid. Knoop X (categorie 1, vraag 1) kan uit beide trekken;
    knoop Y (categorie 2, vraag 1) alleen uit de eerste. Lexicografisch krijgt X zijn
    eenheid - maar WAARUIT is vrij, en dat bepaalt of Y nog iets krijgt. Greedy zonder
    vooruitkijken kan de eerste bron pakken en Y op nul zetten, terwijl er een toewijzing
    bestaat waarin beide volledig gedekt zijn.

    Danna e.a. (INFOCOM 2012): bij meerdere paden per afnemer is er geen combinatorisch
    algoritme bekend en moet je terugvallen op een reeks LP's.

    `SystemState` verbiedt fan-out vandaag - `from_polders` raist bij meer dan één uitgaande
    verbinding - dus dit is geen bug maar een grens. Deze test staat er zodat die grens
    expliciet is en niet impliciet, en hij faalt luidruchtig zodra iemand fan-out toestaat
    zonder de toewijzing aan te passen.
    """
    with pytest.raises(ValueError, match="uitgaande"):
        SystemState.from_polders(
            [
                PolderState(
                    area_ha=1000,
                    pct_open_water=3.5,
                    connections=(
                        Connection(to="bron_a", capacity_in_m3_per_sec=1.0),
                        Connection(to="bron_b", capacity_in_m3_per_sec=1.0),
                    ),
                ),
                _node(1.0),
                _node(1.0),
            ],
            names=["x", "bron_a", "bron_b"],
        )

    # en dit is de suboptimaliteit die dan zou ontstaan, op losse getallen
    greedy_takes_the_contested_source = {"x": 1.0, "y": 0.0}
    optimal = {"x": 1.0, "y": 1.0}
    assert sum(greedy_takes_the_contested_source.values()) < sum(optimal.values())


def test_the_weighted_form_refuses_instead_of_inventing_weights():
    """De wettelijke vorm is niet gebouwd, en de reden is niet technisch.

    De gewichten zijn de marginale schade per m3, en die hebben wij niet. Ze verzinnen is
    hier hetzelfde als een prijs verzinnen voor peilopzet - dus raist hij, met de reden.
    """
    system = SystemState.from_polders([_node(1.0)], names=["a"])
    with pytest.raises(NotImplementedError, match="gewichten"):
        allocate(
            system,
            np.array([MILLION]),
            np.array([4]),
            MILLION,
            DAYS,
            rule=WithinShellRule.WEIGHTED,
        )


def test_the_allocation_scales_to_a_national_selection():
    """8500 afnemers op één boezem, en de water-filling blijft goedkoop.

    Het aantal ronden is ten hoogste het aantal klemmen, niet het aantal afnemers, en elke
    ronde is twee gevectoriseerde passes. Gemeten 22 ms; de grens staat ruim zodat een
    tragere machine hem niet haalt maar een ontspoorde lus wel.
    """
    import time

    rng = np.random.default_rng(1)
    count = 8500
    polders = [_node(float(rng.uniform(0.01, 0.5)), "boezem") for _ in range(count)]
    polders.append(_node(50.0))
    system = SystemState.from_polders(
        polders, names=[f"c{i}" for i in range(count)] + ["boezem"]
    )
    demand = np.concatenate([rng.uniform(0.1, 3.0, count) * MILLION, [0.0]])
    categories = np.concatenate([rng.integers(1, 5, count), [4]])

    allocate(system, demand, categories, 0.4 * demand.sum(), DAYS)  # warm
    start = time.perf_counter()
    result = allocate(system, demand, categories, 0.4 * demand.sum(), DAYS)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 500, f"{elapsed_ms:.0f} ms"
    # de boezem is hier de keel: 50 m3/s over 30 dagen is 129,6 mln m3
    assert result.granted_m3.sum() == pytest.approx(50.0 * SECONDS, rel=1e-9)
    assert result.binding_category == 1


# --- de theta-trap: analytisch, en de sweep is de test -------------------------------


def test_the_handover_is_where_a_category_fills_up(three_consumers):
    """De knikpunten zijn de cumulatieve vraag per categorie, en dat is na te rekenen.

    Totale vraag 6 mln. Categorie 2 vraagt 1, dus vol bij theta = 1/6. Categorie 3 vraagt 2,
    dus cumulatief 3 mln en vol bij theta = 0,5. Categorie 4 vraagt 3 maar kan door zijn
    inlaat maar 2,592 mln, dus het laatste knikpunt ligt op 5,592/6 = 0,932 - en niet op 1,0.
    """
    thetas = theta_breakpoints(three_consumers, DEMAND, CATEGORIES, DAYS)

    def contains(value):
        return any(abs(theta - value) < 1e-9 for theta in thetas)

    assert thetas[0] == pytest.approx(0.0)
    assert thetas[-1] == pytest.approx(1.0)
    assert contains(1 / 6), thetas
    assert contains(0.5), thetas
    assert contains((1.0 * SECONDS + 3 * MILLION) / (6 * MILLION)), thetas


def test_the_theta_table_reads_as_a_staircase(three_consumers):
    """De uitlezing die een waterschap wil: vanaf hier valt deze categorie af."""
    table = theta_table(three_consumers, DEMAND, CATEGORIES, DAYS)

    # de dekking is continu, dus de rechterrand van een stuk is de linkerrand van het volgende
    for lower, upper in zip(table, table[1:]):
        assert lower.theta_high == pytest.approx(upper.theta_low)

    # en de dekking van een stuk is dus een BEREIK: op de rechterrand van het ene stuk
    # staat hetzelfde getal als op de linkerrand van het volgende
    for lower, upper in zip(table, table[1:]):
        assert lower.coverage_at_high == pytest.approx(upper.coverage_at_low)

    # De bindende categorie is die BINNEN het stuk, en niet die op de rechterrand. Op zo'n
    # rand raakt per definitie een categorie vol - dat is wat een knikpunt is - en daar
    # stond dus het regime van het volgende stuk. Bij een derde van de vraag als aanbod is
    # categorie 2 vol, categorie 3 half en categorie 4 leeg, dus 3 bindt; op de rand bij
    # 50 % is 3 net vol en bindt 4.
    at_a_third = next(r for r in table if r.theta_low <= 1 / 3 < r.theta_high)
    assert at_a_third.binding_category == 3
    assert at_a_third.coverage_at_low[3] == pytest.approx(0.0)
    assert at_a_third.coverage_at_high[3] == pytest.approx(1.0)
    assert at_a_third.coverage_at_high[4] == pytest.approx(0.0)


def test_extra_water_beyond_a_binding_intake_buys_nothing(three_consumers):
    """Het laatste stuk van de trap is vlak, en dat is informatie en geen artefact.

    Voorbij theta = 0,932 is er meer water dan landbouw door zijn inlaat krijgt. Dat de trap
    daar een eigen stuk heeft, is precies wat je wil weten: hier koopt aanbod niets meer, en
    de vraag is niet "meer water" maar "een grotere inlaat".
    """
    table = theta_table(three_consumers, DEMAND, CATEGORIES, DAYS)
    last, before = table[-1], table[-2]

    assert last.coverage_at_high == pytest.approx(before.coverage_at_high)
    assert last.coverage_at_high[4] == pytest.approx(1.0 * SECONDS / (3 * MILLION))

    # En dat is precies de reden dat deze twee treden niet zijn samengevoegd, terwijl hun
    # dekking gelijk is: de AARD van de binding slaat hier om. Daarvoor is er te weinig
    # water, daarna past het er niet doorheen - een rantsoeneringsvraag tegenover een
    # kunstwerkvraag. Zonder die vlag is dat verschil uit de trap niet af te lezen.
    assert last.binding_is_capacity_not_availability
    assert not before.binding_is_capacity_not_availability


def test_adjacent_steps_that_say_the_same_thing_are_merged(three_consumers):
    """Een trede die niets toevoegt is een trede die suggereert dat er iets ontbreekt."""
    table = theta_table(three_consumers, DEMAND, CATEGORIES, DAYS)
    for lower, upper in zip(table, table[1:]):
        assert (
            lower.coverage_at_high,
            lower.binding_category,
            lower.binding_is_capacity_not_availability,
        ) != (
            upper.coverage_at_high,
            upper.binding_category,
            upper.binding_is_capacity_not_availability,
        )


def test_the_breakpoints_are_analytic():
    """De kern van #31 stap 3: de knikpunten worden niet gezocht maar geproduceerd.

    Een dichte sweep over duizend theta's moet exact op de stuksgewijs-lineaire
    reconstructie tussen de knikpunten liggen. Ligt hij dat, dan zijn de critical regions van
    Gal & Nedoma een BIJPRODUCT van het antwoord en geen aparte berekening - en dan is zowel
    de sweep als multiparametrisch LP een omweg.

    De sweep is hier dus de test en niet het antwoord.
    """
    rng = np.random.default_rng(31)
    worst = 0.0
    for _ in range(12):
        system, demand, categories, _ignored = _random_two_level_system(rng)
        total = float(demand.sum())
        if total <= 0:
            continue
        thetas = np.array(theta_breakpoints(system, demand, categories, DAYS))
        # de toewijzing per categorie op elk knikpunt; daartussen hoort hij lineair te zijn
        present = sorted(set(int(c) for c in categories))
        knots = {
            category: np.array(
                [
                    allocate(system, demand, categories, theta * total, DAYS)
                    .granted_m3[categories == category]
                    .sum()
                    for theta in thetas
                ]
            )
            for category in present
        }
        for theta in np.linspace(0.0, 1.0, 1000):
            actual = allocate(system, demand, categories, theta * total, DAYS)
            for category in present:
                expected = np.interp(theta, thetas, knots[category])
                got = actual.granted_m3[categories == category].sum()
                worst = max(worst, abs(got - expected) / max(total, 1.0))
    assert worst < 1e-9, f"grootste relatieve afwijking van lineair: {worst:.2e}"


# --- maximin: dezelfde lus, andere weegvector ---------------------------------------


def test_maximin_gives_everyone_the_same_volume_not_the_same_fraction(three_consumers):
    """Het verschil tussen de twee vormen, op de referentiecasus.

    Vraag 1, 2 en 3 miljoen m3, aanbod 3 miljoen, alles in een categorie. Gelijk tekort
    geeft ieder 50 % van zijn vraag - 0,5, 1,0 en 1,5. Maximin geeft ieder hetzelfde VOLUME
    tot zijn vraag: 1 miljoen elk, en dan zit de kleinste vrager vol.

    De wet zegt geen van beide. Daarom zijn ze samen een band en niet twee kandidaten.
    """
    same_shell = np.array([4, 4, 4, 4])

    equal_deficit = allocate(
        three_consumers,
        DEMAND,
        same_shell,
        3 * MILLION,
        DAYS,
        rule=WithinShellRule.PROPORTIONAL,
    )
    maximin = allocate(
        three_consumers,
        DEMAND,
        same_shell,
        3 * MILLION,
        DAYS,
        rule=WithinShellRule.MAXIMIN,
    )

    assert equal_deficit.granted_m3[:3] == pytest.approx(
        [0.5 * MILLION, 1.0 * MILLION, 1.5 * MILLION]
    )
    assert maximin.granted_m3[:3] == pytest.approx([MILLION, MILLION, MILLION])


def test_maximin_lifts_the_smallest_volume_not_the_smallest_fraction(three_consumers):
    """De definiërende eigenschap, en let op WELKE grootheid.

    Maximin maximaliseert het kleinste VOLUME. In dekkingsfractie kan hij juist harder zijn
    dan gelijk tekort: op een net met een grote, een middelgrote en een kleine vrager gaat de
    grootste van 50 % naar 31 % dekking terwijl de kleinste van 50 % naar 100 % gaat.

    Dat is geen fout maar het hele punt van de band: de twee proxies zijn het oneens over wie
    "de slechtst bedeelde" is - de kleinste ontvanger of de grootste gedupeerde. De wet zegt
    dat niet, en dus mogen wij het ook niet zeggen.
    """
    same_shell = np.array([4, 4, 4, 4])
    for available in (0.5, 1.5, 3.0, 5.0):
        kwargs = dict(available_m3=available * MILLION)
        equal_deficit = allocate(
            three_consumers,
            DEMAND,
            same_shell,
            kwargs["available_m3"],
            DAYS,
            rule=WithinShellRule.PROPORTIONAL,
        )
        maximin = allocate(
            three_consumers,
            DEMAND,
            same_shell,
            kwargs["available_m3"],
            DAYS,
            rule=WithinShellRule.MAXIMIN,
        )
        assert maximin.granted_m3[:3].min() >= equal_deficit.granted_m3[:3].min() - 1.0


def test_both_forms_use_the_same_amount_of_water():
    """De vorm bepaalt WIE het krijgt, niet HOEVEEL er wordt gebruikt.

    Beide vullen tot de bron of een keel klemt, dus het totaal per categorie is gelijk. Dat
    is de zin die een bestuurder nodig heeft voordat de keuze een keuze wordt - en het maakt
    de LP-toets ook geldig voor maximin, want die toetst juist die totalen.
    """
    rng = np.random.default_rng(1403)
    worst = 0.0
    for _ in range(80):
        system, demand, categories, available = _random_two_level_system(rng)
        totals = {}
        for rule in (WithinShellRule.PROPORTIONAL, WithinShellRule.MAXIMIN):
            result = allocate(system, demand, categories, available, DAYS, rule=rule)
            totals[rule] = {
                category: result.granted_m3[categories == category].sum()
                for category in sorted(set(int(c) for c in categories))
            }
        scale = max(float(demand.sum()), 1.0)
        for category, value in totals[WithinShellRule.PROPORTIONAL].items():
            worst = max(
                worst, abs(value - totals[WithinShellRule.MAXIMIN][category]) / scale
            )
    assert worst < 1e-9, f"grootste relatieve verschil in categorietotaal: {worst:.2e}"


def test_maximin_matches_the_reference_lp_on_the_category_totals():
    """En dus geldt de LP-toets ook voor maximin, met dezelfde tolerantie."""
    rng = np.random.default_rng(97)
    worst, compared = 0.0, 0
    for _ in range(40):
        system, demand, categories, available = _random_two_level_system(rng)
        result = allocate(
            system, demand, categories, available, DAYS, rule=WithinShellRule.MAXIMIN
        )
        for category, expected in _lp_category_totals(
            system, demand, categories, available
        ).items():
            got = result.granted_m3[categories == category].sum()
            scale = max(float(demand[categories == category].sum()), 1.0)
            worst = max(worst, abs(got - expected) / scale)
            compared += 1
    assert compared > 60
    assert worst < 1e-9, f"grootste relatieve afwijking {worst:.2e}"


def test_maximin_does_not_depend_on_the_order_of_the_consumers(three_consumers):
    """De max-min fair oplossing is uniek (Le Boudec Thm 1.2.2), dus de orde doet niets."""
    same_shell = np.array([4, 4, 4, 4])
    forward = allocate(
        three_consumers,
        DEMAND,
        same_shell,
        2.2 * MILLION,
        DAYS,
        rule=WithinShellRule.MAXIMIN,
    )

    order = [2, 1, 0, 3]
    shuffled = SystemState.from_polders(
        [_node(1.0, "boezem"), _node(1.0, "boezem"), _node(1.0, "boezem"), _node(10.0)],
        names=["landbouw", "industrie", "drinkwater", "boezem"],
    )
    backward = allocate(
        shuffled,
        DEMAND[order],
        same_shell,
        2.2 * MILLION,
        DAYS,
        rule=WithinShellRule.MAXIMIN,
    )
    assert backward.granted_m3 == pytest.approx(forward.granted_m3[order])


def test_the_two_proxies_disagree_about_who_bears_the_shortfall():
    """De band, en waar hij zit: niet in het totaal maar in de verdeling.

    Drie afnemers van heel verschillende grootte in een categorie, vraag 4 / 1,5 / 0,5 mln,
    aanbod 3 mln. Beide vormen gebruiken exact dezelfde 3 miljoen - het categorietotaal is
    50 % in beide gevallen - maar gelijk tekort legt het tekort proportioneel neer (ieder
    50 %) en maximin bij de grootste vrager (31 %, 83 %, 100 %).

    Dit is de zin die naar buiten moet: hoeveel water er omgaat is een modeluitkomst, wie het
    krijgt is een beleidskeuze. Ze verwarren is precies de fout die #30 op de natte kant
    aanwijst.
    """
    system = SystemState.from_polders(
        [_node(2.0, "boezem"), _node(2.0, "boezem"), _node(2.0, "boezem"), _node(10.0)],
        names=["groot", "midden", "klein", "boezem"],
    )
    demand = np.array([4.0, 1.5, 0.5, 0.0]) * MILLION
    categories = np.array([4, 4, 4, 4])

    equal_deficit = allocate(
        system,
        demand,
        categories,
        3 * MILLION,
        DAYS,
        rule=WithinShellRule.PROPORTIONAL,
    )
    maximin = allocate(
        system,
        demand,
        categories,
        3 * MILLION,
        DAYS,
        rule=WithinShellRule.MAXIMIN,
    )

    # zelfde totaal
    assert equal_deficit.coverage_of_category(4) == pytest.approx(0.5)
    assert maximin.coverage_of_category(4) == pytest.approx(0.5)

    # andere verdeling: gelijk tekort is vlak, maximin loopt uiteen
    assert equal_deficit.coverage[:3] == pytest.approx([0.5, 0.5, 0.5])
    assert maximin.coverage[0] < 0.35
    assert maximin.coverage[2] == pytest.approx(1.0)

    # en het kleinste VOLUME is bij maximin wel groter
    assert maximin.granted_m3[:3].min() > equal_deficit.granted_m3[:3].min()
