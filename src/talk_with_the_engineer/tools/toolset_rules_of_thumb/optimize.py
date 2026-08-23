"""De pakketzoeker: het goedkoopste maatregelpakket dat aan twee eisen tegelijk voldoet.

`solve` is de inverse van *één* maatregel. Dit is iets anders, en die twee bewust niet in
één functie: zodra er meerdere maatregelen en meerdere eisen zijn, is het geen inverse meer
maar een optimalisatie. Zie issue #28 punt 6.

**Twee eisen, en ze delen een schaarse grootheid.** Peilopzet vergroot de voorraad en
verkleint de marge tot inundatie met exact dezelfde centimeters, dus ze zijn niet los te
optimaliseren:

    dh_total_above_original_datum_m <= inundatienorm
    retained_volume_mm              >= minimale voorraad

Dat is precies wat de demo moet laten zien. Met alleen de inundatie-eis zegt het antwoord
"altijd pompen", want afvoeren is met een lineaire prijs bij elke ambitie het goedkoopst.
Voeg de voorraadeis toe en er komt een maatregel bij: afvoeren draagt niets bij aan de
voorraad, bergen aan beide, en peilopzet is de enige die voorraad direct koopt.

**En welk pakket het dan wordt, hangt aan een prijs die er niet is.** Peilopzet kost geen
euro's maar drooglegging. Zolang die prijs op nul stond, kocht opzet inundatiemarge die een
groter gemaal terugverdiende, en won `{afvoeren, peilopzet}`. Vanaf ongeveer 0,14 miljoen
euro per centimeter komt bergen erbij, en bij 1,5 miljoen verdwijnt afvoeren helemaal - dan
staat er het pakket dat eerder als "de trits ontstaat uit het model" was opgeschreven. Die
uitspraak was dus een gevolg van een ontbrekende prijs en niet van de hydrologie. Wat er nu
staat is de prijsas: zie `Package.priceless` en `switch_price_of`, en issue #30.

**De vorm: enumeratie buiten, continu binnen.** Vier actietypen geeft vijftien niet-lege
mixen; per mix wordt de goedkoopste maatvoering gezocht met SLSQP. Geen genetisch algoritme
en geen Bayesiaanse optimalisatie - de dimensie is vier, de doorrekening kost 0,06 ms, en
het antwoord moet uit te leggen zijn. "We enumereren de mixen en lossen de continue
hoeveelheden op tegen de twee eisen" is auditeerbaar; een black box niet.
"""

from dataclasses import dataclass, field
from itertools import combinations
from typing import NamedTuple

import numpy as np
from scipy.optimize import minimize

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AfvoerenAction,
    BergenAction,
    PeilopzetAction,
    UnitCost,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureRole,
    round_significant,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

DEFAULT_ACTIONS = (
    VasthoudenAction(),
    BergenAction(),
    AfvoerenAction(),
    PeilopzetAction(),
)
"""De vier acties, in de volgorde van de trits met peilopzet erachter.

De volgorde is niet vrij: `apply` wordt sequentieel toegepast en bergen verandert het
landoppervlak waar vasthouden zijn fractie tegen rekent. Vasthouden eerst houdt die
conversie tegen de oorspronkelijke toestand, wat de leesbare keuze is - "30 % van het land"
betekent dan 30 % van het land dat er nu ligt.
"""

FEASIBILITY_TOLERANCE = 1e-6
"""Hoe ver een eis gemist mag worden voordat een pakket onhaalbaar heet.

Bewust absoluut en bewust strak op BEIDE eisen, ook al staan ze in verschillende eenheden.
Een strenge haalbaarheidstoets zit aan de veilige kant - je wijst dan een pakket af dat er
een nanometer naast zit - en die kant is hier de goede. Dat is iets anders dan `eps_of`,
dat een RAPPORTAGEdrempel is en daarom wel per eenheid moet kloppen.
"""
NEGLIGIBLE_FRACTION = 1e-4
"""Onder deze fractie van de bovengrens is een maatvoering ruis en geen maatregel."""
GRADIENT_STEP = 1e-4
COST_SCALE = 1e-6
"""SLSQP's `ftol` is betekenisloos op kosten in miljoenen; we zoeken in miljoenen euro's."""
EPS_LEVEL_M = 1e-3
"""Wanneer de inundatie-eis "op zijn grens" ligt: een millimeter op de waterstand.

Een millimeter en niet minder, want het model is een vuistregel; een millimeter en niet
meer, want de massabalans sluit op 1e-12 en het zou zonde zijn die precisie weg te gooien
op de plek waar hij er wel is.
"""
SWEEP_POINTS = 33
"""Rasterpunten voor de eendimensionale sweep per maatregel; zie `sweep_measure`."""


def eps_of(state: PolderState) -> dict[str, float]:
    """De rapportagedrempel per eis, elk in de eenheid van díe eis.

    Hier zat een echte fout. `binding` deed `abs(margin) <= 1e-3` over een dict waarin de
    inundatiemarge in METER staat en de voorraadmarge in MILLIMETER. Dat is 1 mm op de
    stand en 1 MICROMETER op de voorraad - duizend keer strakker op de tweede eis, zonder
    dat iemand dat zo bedoeld heeft.

    Eén getal kan dus niet, en twee losse getallen zouden twee afspraken zijn. Daarom leidt
    de tweede zich af uit de eerste, via het model zelf: `EPS_LEVEL_M` peilopzet koopt
    `open water-aandeel * 1000` millimeter voorraad. Bij 3,5 % open water is dat 0,035 mm.
    Dan zijn beide drempels dezelfde fysieke uitspraak - "een millimeter peil" - en schaalt
    de tweede automatisch mee met de polder.

    Op de begintoestand en niet op de toestand ná de maatregelen: bergen verandert het
    open-wateraandeel, en een drempel die per pakket verschuift maakt pakketten
    onvergelijkbaar. Een drempel hoort van de vraag te zijn, niet van het antwoord.
    """
    return {
        "inundatie": EPS_LEVEL_M,
        "voorraad": EPS_LEVEL_M * state.pct_open_water / 100.0 * 1000.0,
    }


@dataclass(frozen=True)
class Constraints:
    """De twee eisen. `None` betekent: deze eis wordt niet gesteld."""

    max_dh_total_m: float | None = None
    """Inundatienorm, gemeten boven het OORSPRONKELIJKE peil - dus inclusief peilopzet."""
    min_storage_mm: float | None = None
    """Minimale voorraad onder het streefpeil, in mm over de polder."""

    @property
    def any_set(self) -> bool:
        return self.max_dh_total_m is not None or self.min_storage_mm is not None


@dataclass
class Package:
    """Een maatregelpakket met zijn maatvoering, prijs en de uitkomst ervan."""

    quantities: dict[str, float]
    cost: float
    """Investeringskosten van de maatregelen die een prijs HEBBEN [EUR].

    Dus niet de prijs van het pakket zodra `priceless` niet leeg is. Wat er dan ontbreekt
    staat in `priceless`, en wat het zou moeten kosten voordat het antwoord verandert in
    `switch_price_of`.
    """
    state_after: PolderState
    dh_total_m: float
    storage_mm: float
    feasible: bool
    binding: tuple[str, ...] = field(default_factory=tuple)
    """Welke eisen precies op hun grens liggen; dat is waar de prijs vandaan komt."""
    priceless: tuple[str, ...] = field(default_factory=tuple)
    """Maatregelen die worden ingezet en geen prijs hebben.

    Peilopzet en aanvoeren kosten geen aanleg maar drooglegging respectievelijk water, en
    dat is een verdringingsvraagstuk. Eerder werd `cost()` hier met `or 0.0` op nul gezet,
    en daarmee werd "geen prijs" stil "gratis" - met gevolgen voor de UITKOMST, niet alleen
    voor de rapportage: peilopzet kocht dan inundatiemarge die een groter gemaal
    terugverdiende, en het goedkoopste pakket verschoof van bergen naar afvoeren. Zie
    issue #30 en `switch_price_of`.
    """
    cost_range: tuple[float, float] | None = None
    """Onder- en bovengrens van de investeringskosten [EUR], of `None`.

    `None` zodra er een prijsloze maatregel in het pakket zit: dan is er geen prijs, en dus
    ook geen band om een prijs. De band zelf komt uit `UnitCost.low/high` en is dus per
    maatregel verschillend - het gemaal staat op -3/+6 %, bergen op -11/+70 %.
    """
    replacement_cost: float = 0.0
    """Dezelfde maatvoering, geprijsd als VERVANGING in plaats van als toename [EUR].

    Een tweede lezing en geen correctie. Lineair rekenen is een bewuste
    vuistregelvereenvoudiging; de trapkost is wat een gemaal werkelijk kost. Het verschil is
    op de referentiepolder een factor 2,7, en het verandert de RANGORDE - zie
    `indistinguishable_under_step_cost`.
    """
    replacement_cost_range: tuple[float, float] = (0.0, 0.0)
    """De prijsband van die tweede lezing; het criterium voor "niet te onderscheiden"."""
    priced_cost_range: tuple[float, float] = (0.0, 0.0)
    """Dezelfde band, maar over het deel dat WEL een prijs heeft; altijd aanwezig.

    Dit is de maat voor wat we van prijzen weten, en daarmee de epsilon die het
    bijna-optimale gebied definieert: twee pakketten zijn niet te onderscheiden zodra hun
    kostenintervallen overlappen. Dat is het epsilon-dominantie-criterium (Laumanns e.a.
    2002) met een getal dat het model zelf levert in plaats van een afgesproken percentage.
    Zie `cost_epsilon`.
    """


@dataclass(frozen=True)
class MeasureRange:
    """Wat een maatregel in het bijna-optimale gebied doet, en tussen welke grenzen.

    De twee grenzen komen uit twee verschillende dingen, en dat is het hele punt:

    * `magnitude_min` uit de **eis** - minder haalt de norm niet;
    * `magnitude_max` uit de **prijsband** - meer koopt niets meer binnen wat we van de
      prijzen weten.

    Geen van beide komt uit de optimizer. Daarom is dit interval per constructie
    zoekeronafhankelijk: Linux en macOS geven hetzelfde gebied, ook waar ze een ander punt
    zouden kiezen. Dat is een sterkere garantie dan een afgesproken tolerantie.

    Coördinaatgewijs, dus een ondergrens op de werkelijke speelruimte; zie `ranges_of`.
    """

    name_nl: str
    unit: str
    magnitude_min: float
    magnitude_max: float
    role: MeasureRole


@dataclass
class OptimizeResult:
    best: Package | None
    packages: tuple[Package, ...]
    """Alle onderzochte mixen, ook de onhaalbare. Dat maakt het antwoord navolgbaar."""
    problem_infeasible: bool
    """Geen enkele mix haalt de eisen. Dit is de PROBLEM_INFEASIBLE uit `SolveStatus`."""
    near_optimal: tuple[Package, ...] = field(default_factory=tuple)
    """De ONDERSCHEIDEN pakketten die binnen de prijsband even goed zijn.

    Ontdubbeld op maatvoering, en dat is geen kosmetiek. Van de vijftien mixen zijn er op de
    referentiecasus twaalf haalbaar en drie onderscheiden: zes mixen geven letterlijk
    hetzelfde `{afvoeren 2,91}`, omdat de extra maatregelen naar nul worden gedreven en de
    mix samenvalt met een kleinere. `packages` is dus niet het gebied - het is één punt, tot
    vijftien keer. Zie `distinct_answers`.
    """
    ranges: tuple[MeasureRange, ...] = field(default_factory=tuple)
    """Per maatregel het interval en de rol; de uitspraak die een waterschap kan lezen.

    Dit is wat er in plaats van `best` naar buiten hoort: niet "2,91 m3/s" maar "een groter
    gemaal zit in elk pakket dat alleen droog diept, en de maatvoering mag van 2,9 tot 3,4".
    """


def _apply_all(state: PolderState, actions, quantities) -> PolderState:
    for action, quantity in zip(actions, quantities):
        state = action.at(max(float(quantity), 0.0)).apply(state)
    return state


class Outcome(NamedTuple):
    """Wat één doorrekening oplevert: twee uitlezingen, de prijs, en wat er geen prijs had.

    Een `NamedTuple` en geen tuple, omdat er een vijfde veld bij kwam: `outcome_of(...)[3]`
    en indexeren blijven werken, maar de velden hebben nu een naam en dat is op de plekken
    waar er drie van de vijf worden weggegooid een stuk leesbaarder.
    """

    state_after: PolderState
    dh_total_m: float
    """Stijging boven het OORSPRONKELIJKE peil, dus inclusief peilopzet."""
    storage_mm: float
    cost: float
    """Alleen de maatregelen die een prijs hebben; zie `priceless`."""
    priceless: tuple[str, ...]
    """Ingezette maatregelen zonder prijs. Zie `Package.priceless`."""


def outcome_of(state: PolderState, storm, actions, quantities) -> Outcome:
    """De twee uitlezingen van dezelfde doorrekening, plus de prijs.

    Eén simulatie, twee vragen - het world-modelargument zonder retoriek. `dh_total` telt de
    peilopzet mee omdat een inundatienorm boven het oorspronkelijke peil geldt en niet boven
    het opgezette.

    Hier stond eerder `cost(state) or 0.0`, en die `or` maakte van "geen prijs" een prijs
    van nul - met gevolgen voor de uitkomst en niet alleen voor de rapportage. Zie
    `Package.priceless`.
    """
    after = _apply_all(state, actions, quantities)
    result = simulate(after, storm)
    cost = 0.0
    priceless = []
    for action, quantity in zip(actions, quantities):
        magnitude = max(float(quantity), 0.0)
        price = action.at(magnitude).cost(state)
        if price is None:
            # een prijsloze maatregel die niet wordt ingezet is geen ontbrekende prijs
            if magnitude > 0.0:
                priceless.append(action.name_nl)
            continue
        cost += price
    return Outcome(
        state_after=after,
        dh_total_m=result.dh_total_above_original_datum_m,
        storage_mm=after.retained_volume_mm,
        cost=cost,
        priceless=tuple(priceless),
    )


def replacement_cost_of(state: PolderState, actions, quantities):
    """De prijs en de band in de TRAPKOST-lezing.

    Alleen afvoeren wijkt hier af van de lineaire lezing; bergen en vasthouden zijn werkelijk
    lineair in het areaal. Dat maakt dit geen aparte prijslijst maar dezelfde prijslijst met
    een andere grondslag voor een van de vier maatregelen.
    """
    total = 0.0
    low = high = 0.0
    for action, quantity in zip(actions, quantities):
        applied = action.at(max(float(quantity), 0.0))
        price = applied.replacement_cost(state)
        if price is None:
            continue
        total += price
        band = applied.replacement_cost_range(state)
        low += band[0]
        high += band[1]
    return total, (low, high)


def cost_range_of(state: PolderState, actions, quantities) -> tuple[float, float]:
    """Onder- en bovengrens van de prijs van de maatregelen die een prijs HEBBEN [EUR].

    De som van `Action.cost_range`, en die verschilt per maatregel omdat `UnitCost` per
    maatregel een eigen herkomst en dus een eigen bandbreedte heeft.

    Deze band heeft twee verschillende taken, en het is de moeite die te scheiden:

    * als **prijs van het pakket** hoort hij te ontbreken zodra er een prijsloze maatregel
      in zit - een band om een getal dat niet bestaat is erger dan geen band. Dat is
      `Package.cost_range`, en die is dan `None`.
    * als **maat voor wat we van prijzen weten** blijft hij bruikbaar, want over het deel
      dat we wel geprijsd hebben weten we nog precies zo veel. Dat is
      `Package.priced_cost_range`, en die is er altijd.

    Zonder dat onderscheid klapt het bijna-optimale gebied dicht zodra peilopzet meedoet:
    geen band betekent epsilon nul betekent een interval van nul breed, en dan meldt de
    zoeker weer een punt - precies waar issue #30 over gaat.
    """
    low = high = 0.0
    for action, quantity in zip(actions, quantities):
        band = action.at(max(float(quantity), 0.0)).cost_range(state)
        if band is None:
            continue
        low += band[0]
        high += band[1]
    return low, high


def _finite_difference(function, x, step=GRADIENT_STEP):
    """Centrale differenties. De gradiënt die SLSQP nodig heeft, expliciet en getest.

    Bewust geen `jac=None`: dan doet scipy voorwaartse differenties met een eigen stap, en
    dan is de gradiënt een implementatiedetail van de optimizer in plaats van iets van ons.
    Bij vier variabelen en 0,06 ms per doorrekening kost dit acht simulaties, dus een halve
    milliseconde.

    Dit is O(aantal variabelen) simulaties. Op polderschaal is dat gratis; op nationale
    schaal is het precies de reden dat de adjoint uit §7 nodig is - daar zou dit het aantal
    knopen keer een simulatie kosten in plaats van één backward pass.
    """
    x = np.asarray(x, dtype=float)
    gradient = np.zeros_like(x)
    for index in range(len(x)):
        forward, backward = x.copy(), x.copy()
        forward[index] += step
        backward[index] -= step
        gradient[index] = (function(forward) - function(backward)) / (2 * step)
    return gradient


def _package_from(state: PolderState, storm, actions, quantities, constraints):
    highs = np.array([action.upper_bound(state) for action in actions])
    quantities = np.clip(quantities, 0.0, highs)
    quantities = np.where(quantities < NEGLIGIBLE_FRACTION * highs, 0.0, quantities)

    after, dh_total, storage, cost, priceless = outcome_of(
        state, storm, actions, quantities
    )
    margins = {}
    if constraints.max_dh_total_m is not None:
        margins["inundatie"] = constraints.max_dh_total_m - dh_total
    if constraints.min_storage_mm is not None:
        margins["voorraad"] = storage - constraints.min_storage_mm

    priced_band = cost_range_of(state, actions, quantities)
    replacement, replacement_band = replacement_cost_of(state, actions, quantities)
    eps = eps_of(state)
    feasible = all(margin >= -FEASIBILITY_TOLERANCE for margin in margins.values())
    binding = tuple(
        name for name, margin in margins.items() if abs(margin) <= eps[name]
    )
    return Package(
        quantities={
            action.name_nl: float(quantity)
            for action, quantity in zip(actions, quantities)
        },
        cost=float(cost),
        state_after=after,
        dh_total_m=float(dh_total),
        storage_mm=float(storage),
        feasible=feasible,
        binding=binding,
        priceless=priceless,
        cost_range=None if priceless else priced_band,
        priced_cost_range=priced_band,
        replacement_cost=replacement,
        replacement_cost_range=replacement_band,
    )


def optimise_mix(
    state: PolderState, storm, actions, constraints: Constraints
) -> Package:
    """Zoek de goedkoopste maatvoering voor één vaste actiemix.

    SLSQP ziet kosten in miljoenen als plat: `ftol=1e-6` is dan een honderdste cent, en
    een startpunt dat al haalbaar is wordt als klaar beschouwd. Op Linux blijft hij
    daardoor op het startpunt staan of vindt hij geen haalbaar punt. Daarom rekenen we
    in miljoenen euro's, starten we bij nul, en proberen we de bovengrens alleen als
    dat eerste punt de eisen mist.
    """
    bounds = [(0.0, action.upper_bound(state)) for action in actions]
    highs = np.array([high for _low, high in bounds])

    def cost_of(x):
        return outcome_of(state, storm, actions, x).cost * COST_SCALE

    def inundation_margin(x):
        """>= 0 als de norm gehaald wordt."""
        return (
            constraints.max_dh_total_m - outcome_of(state, storm, actions, x).dh_total_m
        )

    def storage_margin(x):
        return (
            outcome_of(state, storm, actions, x).storage_mm - constraints.min_storage_mm
        )

    constraint_list = []
    if constraints.max_dh_total_m is not None:
        constraint_list.append(
            {
                "type": "ineq",
                "fun": inundation_margin,
                "jac": lambda x: _finite_difference(inundation_margin, x),
            }
        )
    if constraints.min_storage_mm is not None:
        constraint_list.append(
            {
                "type": "ineq",
                "fun": storage_margin,
                "jac": lambda x: _finite_difference(storage_margin, x),
            }
        )

    def from_start(start):
        solution = minimize(
            cost_of,
            start,
            jac=lambda x: _finite_difference(cost_of, x),
            method="SLSQP",
            bounds=bounds,
            constraints=constraint_list,
            options={"maxiter": 200, "ftol": 1e-6},
        )
        return _package_from(state, storm, actions, solution.x, constraints)

    package = from_start(np.zeros(len(actions)))
    if package.feasible:
        return package
    # Als zelfs de bovengrens de eisen mist, kan deze mix het niet. Geen tweede zoektocht.
    at_bound = _package_from(state, storm, actions, highs, constraints)
    if not at_bound.feasible:
        return package
    retry = from_start(highs)
    if retry.feasible or retry.cost < package.cost:
        return retry
    return package


def optimize(
    state: PolderState,
    storm,
    constraints: Constraints,
    actions=DEFAULT_ACTIONS,
    max_mix_size: int | None = None,
) -> OptimizeResult:
    """Het goedkoopste pakket dat aan de eisen voldoet, over alle actiemixen.

    `max_mix_size` begrenst hoeveel maatregelen er tegelijk mogen worden ingezet. Standaard
    alle - dat is bij vier acties vijftien mixen en dus vijftien SLSQP-runs, samen ruim
    onder een seconde. Wordt hij gezet, dan staat er in de uitvoer welke mixen niet zijn
    onderzocht; stil begrenzen leest als "alles gedekt" terwijl dat niet zo is.
    """
    if not constraints.any_set:
        raise ValueError(
            "geef minstens een eis; zonder eis is het goedkoopste pakket altijd niets doen"
        )

    largest = max_mix_size or len(actions)
    packages = []
    for size in range(1, largest + 1):
        for mix in combinations(actions, size):
            packages.append(optimise_mix(state, storm, mix, constraints))

    feasible = [package for package in packages if package.feasible]
    best = min(feasible, key=lambda package: package.cost) if feasible else None
    if best is None:
        return OptimizeResult(
            best=None, packages=tuple(packages), problem_infeasible=True
        )

    budget = best.cost * (1.0 + cost_epsilon(best))
    near_optimal = tuple(
        package
        for package in distinct_answers(feasible)
        if package.cost <= budget + FEASIBILITY_TOLERANCE
    )
    return OptimizeResult(
        best=best,
        packages=tuple(packages),
        problem_infeasible=False,
        near_optimal=near_optimal,
        ranges=ranges_of(state, storm, actions, near_optimal, constraints, budget),
    )


def used_measures(package: Package) -> tuple[str, ...]:
    """De maatregelen die dit pakket werkelijk inzet, gesorteerd.

    De maatvoering is in `_package_from` al op nul gezet onder `NEGLIGIBLE_FRACTION`, dus
    dit is een schone verzameling en geen drempelvraag. Dat is precies waarom de RANGORDE
    robuuster is dan de maatvoering: WP12 vond 0 van 162 combinaties waarin bergen en
    afvoeren van plaats wisselen, terwijl de hectares een factor honderd bewogen.
    """
    return tuple(
        sorted(name for name, value in package.quantities.items() if value > 0)
    )


def cost_epsilon(package: Package) -> float:
    """Hoe ver twee prijzen uit elkaar mogen liggen om nog hetzelfde te zijn, relatief.

    **Dit getal wordt niet afgesproken, het wordt afgeleid.** De eenheidsprijzen dragen hun
    eigen bandbreedte met hun eigen herkomst - het gemaal staat op -3/+6 % omdat twee
    projecten uit 2024/25 binnen 10 % van elkaar uitkwamen, bergen op -11/+70 % omdat de
    grondprijs regionaal een factor drie verschilt. De relatieve breedte van de band van het
    goedkoopste pakket ís dus de epsilon, en hij is automatisch per maatregelmix anders.

    Dat is beter dan een werkwaarde als "15 %", die voor het gemaal twee keer te ruim is en
    voor bergen vier keer te krap. En het is het criterium uit de epsilon-dominantie
    (Laumanns e.a. 2002): twee oplossingen die dichter bij elkaar liggen dan het model waar
    kan maken, zijn dezelfde oplossing.

    Nul zodra er geen band is - dan zit er een prijsloze maatregel in en is er niets om een
    band om te leggen. Zie `Package.cost_range` en `switch_price_of`.
    """
    low, high = package.priced_cost_range
    if high <= low or package.cost <= 0:
        return 0.0
    return (high - low) / package.cost


def distinct_answers(packages) -> tuple[Package, ...]:
    """De pakketten met een onderscheiden maatvoering, goedkoopste eerst.

    Twee mixen die op dezelfde maatvoering uitkomen zijn één antwoord. Dat gebeurt
    voortdurend: de enumeratie loopt over alle vijftien niet-lege deelverzamelingen, en een
    grotere mix waarin de extra maatregelen naar nul gaan valt samen met een kleinere.

    Afgerond op vier significante cijfers voor de vergelijking, want de vraag is of twee
    antwoorden verschillen en niet of de zoeker op dezelfde bit uitkwam - precies dezelfde
    reden waarom de uitvoer op vier cijfers wordt gemeld.
    """

    def key(package):
        return tuple(
            (name, round_significant(value))
            for name, value in sorted(package.quantities.items())
            if value > 0
        )

    seen, unique = set(), []
    for package in sorted(packages, key=lambda p: p.cost):
        fingerprint = key(package)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(package)
    return tuple(unique)


def sweep_measure(
    state: PolderState, storm, actions, quantities, index, constraints, budget
) -> tuple[float, float] | None:
    """Het interval waarover één maatregel mag bewegen, met de rest vast.

    Raster plus verfijning, en geen bisectie op een monotone aanname. Vasthouden heeft een
    echt binnenoptimum - eerst dalend, dan weer stijgend, zie `solve.minimise_unimodal` -
    dus de haalbaarheid is in de maatvoering niet monotoon, en een bisectie die dat wél
    aanneemt vindt de verkeerde rand. Een raster van 33 punten kost 33 doorrekeningen van
    0,06 ms en is immuun voor de vorm van de curve.

    Levert `None` als geen enkel punt op het raster haalbaar is binnen het budget.

    `budget` is de bovengrens op de prijs van het hele pakket, dus inclusief wat de andere
    maatregelen kosten. Zo is de bovenkant van het interval echt "wat er nog binnen de
    prijsband past" en niet "wat deze maatregel los zou mogen kosten".
    """
    action = actions[index]
    upper = action.upper_bound(state)
    if upper <= 0:
        return None

    trial = list(quantities)

    def admissible(magnitude):
        trial[index] = magnitude
        outcome = outcome_of(state, storm, actions, trial)
        if outcome.cost > budget:
            return False
        if constraints.max_dh_total_m is not None and (
            outcome.dh_total_m > constraints.max_dh_total_m + FEASIBILITY_TOLERANCE
        ):
            return False
        if constraints.min_storage_mm is not None and (
            outcome.storage_mm < constraints.min_storage_mm - FEASIBILITY_TOLERANCE
        ):
            return False
        return True

    grid = np.linspace(0.0, upper, SWEEP_POINTS)
    allowed = [float(x) for x in grid if admissible(float(x))]
    if not allowed:
        return None

    low, high = min(allowed), max(allowed)
    step = float(grid[1] - grid[0])

    # de randen liggen ergens in de rastermaas ernaast; haal ze op met bisectie
    def refine(inside, outside):
        for _ in range(20):
            middle = 0.5 * (inside + outside)
            if admissible(middle):
                inside = middle
            else:
                outside = middle
        return inside

    if low > 0.0:
        low = refine(low, max(low - step, 0.0))
    if high < upper:
        high = refine(high, min(high + step, upper))
    return low, high


def ranges_of(
    state: PolderState, storm, actions, near_optimal, constraints, budget
) -> tuple[MeasureRange, ...]:
    """Per maatregel de rol in het gebied, plus het interval waarover hij mag bewegen.

    De rol komt uit de VERZAMELING pakketten - zit deze maatregel in alle, in sommige, of in
    geen - en het interval uit de sweep rond het goedkoopste pakket, verbreed met wat de
    andere near-optimale pakketten laten zien.

    **Wees precies over wat dit interval is.** Het is coördinaatgewijs: één maatregel
    beweegt en de andere staan vast op hun waarde in het goedkoopste pakket. Dat is niet de
    projectie van het gebied op die as - die is minstens zo breed, want daar mogen de andere
    maatregelen meebewegen. Op de referentiecasus is het verschil zichtbaar: met twee eisen
    komt peilopzet als 0,571 tot 0,571 uit de sweep, omdat elke centimeter meer opzet de
    inundatiemarge opsnoept en het gemaal vaststaat. Laat je het gemaal meebewegen, dan is
    er wel een interval - het is er alleen coördinaatgewijs niet.

    Het interval is dus een ONDERGRENS op de speelruimte, en die kant is de veilige: we
    beweren nooit meer ruimte dan er is. De echte romp is bij vier variabelen exact uit te
    rekenen - de energiemodellen moeten hem juist bij hogere dimensie benaderen - en dat is
    de volgende stap. Tot die tijd hoort in de tekst te staan dat het een ondergrens is.
    """
    if not near_optimal:
        return ()

    best = near_optimal[0]
    quantities = [best.quantities.get(action.name_nl, 0.0) for action in actions]

    ranges = []
    for index, action in enumerate(actions):
        name = action.name_nl
        used_in = [
            package for package in near_optimal if package.quantities.get(name, 0.0) > 0
        ]
        if not used_in:
            role = MeasureRole.ABSENT
        elif len(used_in) == len(near_optimal):
            role = MeasureRole.FORCED
        else:
            role = MeasureRole.OPTIONAL

        magnitudes = [package.quantities.get(name, 0.0) for package in used_in]
        low = min(magnitudes, default=0.0)
        high = max(magnitudes, default=0.0)

        if role is not MeasureRole.ABSENT:
            swept = sweep_measure(
                state, storm, actions, quantities, index, constraints, budget
            )
            if swept is not None:
                low = min(low, swept[0]) if magnitudes else swept[0]
                high = max(high, swept[1])

        ranges.append(
            MeasureRange(
                name_nl=name,
                unit=action.unit,
                magnitude_min=float(low),
                magnitude_max=float(high),
                role=role,
            )
        )
    return tuple(ranges)


def indistinguishable_under_step_cost(result: "OptimizeResult") -> tuple[Package, ...]:
    """De pakketten die in de TRAPKOST-lezing niet van het goedkoopste te onderscheiden zijn.

    **Hier zit het plateau uit issue #30, en niet in de kosten-slack.** Met de lineaire prijs
    is het tweede onderscheiden antwoord op de referentiecasus `{bergen 111 ha}` a 15,01 mln,
    dus +169 % boven `{afvoeren 2,91}` a 5,59 mln - geen enkele redelijke epsilon haalt dat.
    Maar prijs datzelfde gemaal als VERVANGING en het kost 15,19 mln: 1,2 % verschil, met
    prijsbanden die ruim overlappen.

    Dan zijn "een groter gemaal" en "111 hectare open water" twee structureel verschillende
    antwoorden die het model niet uit elkaar kan houden. Dat is een uitspraak die een
    waterschap kan gebruiken, en hij is onzichtbaar zolang er maar een lezing wordt gemeld.

    Criterium: overlappende prijsintervallen, net als bij `cost_epsilon`. Geen afgesproken
    percentage - de banden komen uit `UnitCost` en die is per maatregel onderbouwd. En
    bewust NIET als bredere epsilon op de lineaire lezing: met een factor 2,7 als slack
    slikt de band elk pakket en zegt het plateau niets meer. Twee lezingen naast elkaar,
    niet een brede.
    """
    if result.best is None:
        return ()
    reference = result.best.replacement_cost_range
    if reference[1] <= reference[0]:
        return (result.best,)
    return tuple(
        package
        for package in distinct_answers([p for p in result.packages if p.feasible])
        if max(reference[0], package.replacement_cost_range[0])
        <= min(reference[1], package.replacement_cost_range[1])
    )


@dataclass(frozen=True)
class SwitchPrice:
    """Bij welke prijs een prijsloze maatregel het antwoord verandert.

    Een interval en geen getal, en dat is geen slordigheid maar de eerlijke vorm: de grens
    wordt met bisectie benaderd, en de vergelijking eronder rust op SLSQP. Wat robuust is,
    is aan welke kant van welke ORDEGROOTTE je zit - niet de derde decimaal.
    """

    measure_nl: str
    unit: str
    price_low: float
    """Onder deze prijs per eenheid is het goedkoopste pakket nog `package_below` [EUR]."""
    price_high: float
    """Boven deze prijs is het `package_above` [EUR]."""
    package_below: tuple[str, ...]
    package_above: tuple[str, ...]
    searched_up_to: float
    changed: bool
    """`False` betekent: tot `searched_up_to` verandert er niets. Geen stille afkap."""


def _priced(action, price_per_unit: float):
    """Dezelfde actie met een hypothetische prijs per eenheid.

    `UnitCost` eist `> 0`, en dat is hier de goede beperking: een prijs van nul is iets
    anders dan geen prijs, en juist dat verschil is wat we aan het meten zijn.
    """
    return action.model_copy(
        update={
            "unit_cost": UnitCost(
                typical=price_per_unit,
                low=price_per_unit,
                high=price_per_unit,
                unit=f"EUR per {action.unit}",
                price_level="hypothetisch",
                source="schaduwprijs; geen marktprijs, zie switch_price_of",
            )
        }
    )


def switch_price_of(
    state: PolderState,
    storm,
    constraints: Constraints,
    measure_nl: str,
    actions=DEFAULT_ACTIONS,
    coarse_points: int = 8,
    refinements: int = 6,
    max_mix_size: int | None = None,
) -> SwitchPrice:
    """Welke prijs zou deze maatregel moeten hebben voordat het antwoord verandert?

    Peilopzet en aanvoeren hebben geen prijs, en een prijs verzinnen is erger dan geen
    prijs. Maar `None` laten staan is ook geen antwoord, want dan bepaalt de afwezigheid
    van een getal de uitkomst - met `or 0.0` was peilopzet gratis en verschoof het
    goedkoopste pakket van bergen naar afvoeren.

    Dit is de derde weg, en hij komt uit de MGA-literatuur: niet de prijs invullen maar
    hem AFLEZEN. Je varieert de prijs, optimaliseert opnieuw, en meldt bij welke waarde de
    samenstelling van het goedkoopste pakket omslaat. Dat getal produceert het model; wij
    verzinnen het niet. Voor een waterschap is "peilopzet moet meer dan X per centimeter
    waard zijn voordat bergen wint" een bespreekbare vraag, en "peilopzet heeft geen prijs"
    niet.

    Op de rangorde en niet op de kosten, want dat is de robuuste grootheid. En het
    resultaat is een interval; zie `SwitchPrice`.

    Kosten: `coarse_points + refinements` aanroepen van `optimize`. Dat is geen tool maar
    een analyse, en hij hoort dus niet in een toolaanroep.
    """
    index = next(
        (i for i, action in enumerate(actions) if action.name_nl == measure_nl), None
    )
    if index is None:
        raise ValueError(f"{measure_nl!r} zit niet in deze actieverzameling")
    if actions[index].unit_cost is not None:
        raise ValueError(
            f"{measure_nl!r} heeft al een prijs; een schaduwprijs is alleen zinvol voor "
            "een maatregel die er geen heeft"
        )

    def best_at(price):
        priced = list(actions)
        if price is not None:
            priced[index] = _priced(actions[index], price)
        result = optimize(
            state, storm, constraints, actions=tuple(priced), max_mix_size=max_mix_size
        )
        return result.best

    baseline = best_at(None)
    if baseline is None:
        raise ValueError(
            "zonder prijs is er al geen haalbaar pakket; een schaduwprijs zegt dan niets"
        )
    below = used_measures(baseline)
    magnitude = baseline.quantities.get(measure_nl, 0.0)
    if magnitude <= 0.0:
        # de maatregel wordt niet ingezet, dus een prijs eraan hangen verandert niets
        return SwitchPrice(
            measure_nl=measure_nl,
            unit=actions[index].unit,
            price_low=0.0,
            price_high=float("inf"),
            package_below=below,
            package_above=below,
            searched_up_to=float("inf"),
            changed=False,
        )

    # Ankerschaal: de prijs waarbij deze maatregel het pakket ongeveer zou verdubbelen.
    # Niet willekeurig - het is de enige schaal die het probleem zelf aanreikt, en de
    # omslag ligt er in de praktijk binnen een factor tien van af.
    anchor = max(baseline.cost, 1.0) / magnitude
    grid = anchor * np.geomspace(1 / 64, 16, coarse_points)

    low, high, above = None, None, None
    for price in grid:
        candidate = best_at(float(price))
        if candidate is not None and used_measures(candidate) != below:
            high, above = float(price), used_measures(candidate)
            break
        low = float(price)

    if high is None:
        return SwitchPrice(
            measure_nl=measure_nl,
            unit=actions[index].unit,
            price_low=float(grid[-1]),
            price_high=float("inf"),
            package_below=below,
            package_above=below,
            searched_up_to=float(grid[-1]),
            changed=False,
        )

    low = low if low is not None else 0.0
    for _ in range(refinements):
        middle = 0.5 * (low + high)
        candidate = best_at(middle)
        if candidate is not None and used_measures(candidate) != below:
            high, above = middle, used_measures(candidate)
        else:
            low = middle

    return SwitchPrice(
        measure_nl=measure_nl,
        unit=actions[index].unit,
        price_low=low,
        price_high=high,
        package_below=below,
        package_above=above,
        searched_up_to=float(grid[-1]),
        changed=True,
    )
