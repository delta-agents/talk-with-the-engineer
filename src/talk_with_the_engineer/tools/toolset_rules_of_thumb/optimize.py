"""De pakketzoeker: het goedkoopste maatregelpakket dat aan de eisen tegelijk voldoet.

`solve` is de inverse van *één* maatregel. Dit is iets anders, en die twee bewust niet in
één functie: zodra er meerdere maatregelen en meerdere eisen zijn, is het geen inverse meer
maar een optimalisatie. Zie issue #28 punt 6.

**De eisen delen een schaarse grootheid.** Peilopzet vergroot de voorraad en verkleint de
marge tot inundatie met exact dezelfde centimeters, dus ze zijn niet los te optimaliseren:

    dh_total_above_original_datum_m <= inundatienorm
    retained_volume_mm              >= minimale voorraad        (de peil-as)
    shortfall_mm                    <= maximaal tekort          (de waterstand-as)

Dat is precies wat de demo moet laten zien. Met alleen de inundatie-eis zegt het antwoord
"altijd pompen", want afvoeren is met een lineaire prijs bij elke ambitie het goedkoopst.
Voeg de voorraadeis toe en er komt een maatregel bij: afvoeren draagt niets bij aan de
voorraad, bergen aan beide, en peilopzet is de enige die voorraad direct koopt.

**De derde eis is de droge kant over de tijd, en die verandert wie er mee mag doen.** De
voorraadeis is een uitspraak over de peilband en kent daarom geen inlaat; het tekort komt
uit een doorrekening van een droogteperiode en kent hem wel. Aanvoeren staat dus in
`DEFAULT_ACTIONS` maar doet alleen iets zodra er een `deficit` en een `max_shortfall_mm`
zijn.

**En welk pakket het dan wordt, hangt aan een prijs die er niet is.** Peilopzet kost geen
euro's maar drooglegging. Zolang die prijs op nul stond, kocht opzet inundatiemarge die een
groter gemaal terugverdiende, en won `{afvoeren, peilopzet}`. Vanaf ongeveer 0,14 miljoen
euro per centimeter komt bergen erbij, en bij 1,5 miljoen verdwijnt afvoeren helemaal - dan
staat er het pakket dat eerder als "de trits ontstaat uit het model" was opgeschreven. Die
uitspraak was dus een gevolg van een ontbrekende prijs en niet van de hydrologie. Wat er nu
staat is de prijsas: zie `Package.priceless` en `switch_price_of`, en issue #30.

**De vorm: enumeratie buiten, continu binnen.** Vijf actietypen geeft eenendertig niet-lege
mixen; per mix wordt de goedkoopste maatvoering gezocht met SLSQP. Geen genetisch algoritme
en geen Bayesiaanse optimalisatie - de dimensie is vijf, de doorrekening kost 0,06 ms, en
het antwoord moet uit te leggen zijn. "We enumereren de mixen en lossen de continue
hoeveelheden op tegen de eisen" is auditeerbaar; een black box niet.
"""

from dataclasses import dataclass, field
from itertools import combinations
from typing import NamedTuple

import numpy as np
from scipy.optimize import minimize

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AanvoerenAction,
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
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    simulate,
    simulate_deficit,
)

DEFAULT_ACTIONS = (
    VasthoudenAction(),
    BergenAction(),
    AfvoerenAction(),
    PeilopzetAction(),
    AanvoerenAction(),
)
"""De vijf acties, in de volgorde van de trits met de peil- en aanvoerkant erachter.

De volgorde is niet vrij: `apply` wordt sequentieel toegepast en bergen verandert het
landoppervlak waar vasthouden zijn fractie tegen rekent. Vasthouden eerst houdt die
conversie tegen de oorspronkelijke toestand, wat de leesbare keuze is - "30 % van het land"
betekent dan 30 % van het land dat er nu ligt.

**Aanvoeren doet alleen iets bij een droogte-eis op de waterstand-as** (`max_shortfall_mm`
plus een `deficit`). Bij alleen de statische `min_storage_mm` is hij inert: `simulate` leest
`capacity_in` niet en `retained_volume_mm` bevat hem niet, dus de gradiënt is exact nul.
`_minimise_priceless` verkleint hem dan tot nul in plaats van hem op zijn zoekgrens te
laten staan.

**Peilmarge (voorbemaling) staat hier bewust NIET in.** Voorbemalen is wel degelijk een
investeringsbeslissing - het vraagt telemetrie en sturing, met eigen bedieningsstrategie en
protocollen - maar die investering heeft een váste kostenvorm (je koopt een systeem, geen
centimeters) die deze catalogus met zijn lineaire `UnitCost` nog niet kan dragen. Zolang die
prijs ontbreekt is de maatregel in dit model gratis én gunstig voor beide eisen, en zou de
zoeker hem altijd inzetten en geprijsde maatregelen verdringen. Tot de catalogus een vaste
kostenvorm kent, hoort hij dus in de toestand (`LevelBandInput.level_margin_m`) en niet in
de zoekruimte.
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
BISECTION_STEPS = 40
"""Halveringen om de kleinste toelaatbare maatvoering van een prijsloze maatregel te vinden.

Veertig halveringen brengen een interval van 20 m3/s terug tot 2e-11, dus ruim onder elke
drempel die verderop nog wordt toegepast. Zie `_minimise_priceless`.
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
    Dan zijn beide drempels dezelfde fysieke uitspraak - "een millimeter waterstand" - en schaalt
    de tweede automatisch mee met de polder.

    Op de begintoestand en niet op de toestand ná de maatregelen: bergen verandert het
    open-wateraandeel, en een drempel die per pakket verschuift maakt pakketten
    onvergelijkbaar. Een drempel hoort van de vraag te zijn, niet van het antwoord.
    """
    over_polder = state.pct_open_water / 100.0 * 1000.0
    return {
        "inundatie": EPS_LEVEL_M,
        "voorraad": EPS_LEVEL_M * over_polder,
        # het tekort staat in dezelfde eenheid als de voorraad - mm over de polder - dus
        # dezelfde omrekening, en daarmee opnieuw dezelfde fysieke uitspraak
        "tekort": EPS_LEVEL_M * over_polder,
    }


@dataclass(frozen=True)
class Constraints:
    """De eisen. `None` betekent: deze eis wordt niet gesteld.

    De droogtekant kan op twee manieren worden gesteld, en het verschil is precies de as
    waarop de eis leeft:

    * `min_storage_mm` is een **peil-uitspraak**: de voorraad onder het streefpeil, een
      statische eigenschap van de peilband. Goedkoop - hij kost geen doorrekening - maar
      blind voor alles wat over de tijd loopt. Een inlaat komt er niet in voor.
    * `max_shortfall_mm` is een **waterstand-uitspraak**: wat er na een droogteperiode
      onvervuld blijft, uit `simulate_deficit`. Daar telt een inlaat wel mee, en daarom is
      dit de eis die aanvoeren zichtbaar maakt.
    """

    max_dh_total_m: float | None = None
    """Inundatienorm, gemeten boven het OORSPRONKELIJKE peil - dus inclusief peilopzet."""
    min_storage_mm: float | None = None
    """Minimale voorraad onder het streefpeil, in mm over de polder (de peil-as)."""
    max_shortfall_mm: float | None = None
    """Maximaal onvervuld tekort na de droogteperiode, in mm over de polder.

    Vereist een `deficit` bij de aanroep van `optimize`; zonder droogte is er niets om een
    tekort op te meten.
    """

    @property
    def any_set(self) -> bool:
        return (
            self.max_dh_total_m is not None
            or self.min_storage_mm is not None
            or self.max_shortfall_mm is not None
        )


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
    shortfall_mm: float | None = None
    """Onvervuld tekort na de droogteperiode [mm], of `None` zonder droogte-invoer."""
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
    op de referentiecasus (4000 ha, 3,5 % open water, gemaal 5 m3/s) een factor 2,7, en het
    verandert de RANGORDE - zie
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
    shortfall_mm: float | None = None
    """Onvervuld tekort na de droogteperiode [mm], of `None` zonder droogte-invoer.

    Als laatste veld en met een default, zodat de bestaande positionele uitpak
    (`state_after, dh_total, storage, cost, priceless = outcome_of(...)`) blijft werken
    zolang er geen droogte wordt meegegeven.
    """


def outcome_of(state: PolderState, storm, actions, quantities, deficit=None) -> Outcome:
    """De uitlezingen van dezelfde toestand, plus de prijs.

    Eén maatregelpakket, meerdere vragen - het world-modelargument zonder retoriek.
    `dh_total` telt de peilopzet mee omdat een inundatienorm boven het oorspronkelijke peil
    geldt en niet boven het opgezette.

    Met een `deficit` komt er een TWEEDE doorrekening bij, en dat is geen tweede lezing van
    dezelfde reeks: nat en droog zijn twee verschillende belastingen op dezelfde toestand.
    De natte gebruikt `simulate(after, storm)`, de droge `simulate_deficit(after, deficit)`.
    Zonder droogte-invoer blijft `shortfall_mm` `None` en kost dit niets extra's.

    Let op het verschil tussen "geen prijs" en "een prijs van nul". Een `or 0.0` op de
    kosten maakt van het eerste het tweede, en dat verandert de uitkomst en niet alleen de
    rapportage: een gratis maatregel wint elke vergelijking. Zie `Package.priceless`.
    """
    after = _apply_all(state, actions, quantities)
    result = simulate(after, storm)
    shortfall_mm = (
        float(simulate_deficit(after, deficit).shortfall_mm)
        if deficit is not None
        else None
    )
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
        shortfall_mm=shortfall_mm,
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


def _margins_of(state: PolderState, storm, actions, quantities, constraints, deficit):
    """De marge per gestelde eis; positief betekent gehaald."""
    outcome = outcome_of(state, storm, actions, quantities, deficit)
    margins = {}
    if constraints.max_dh_total_m is not None:
        margins["inundatie"] = constraints.max_dh_total_m - outcome.dh_total_m
    if constraints.min_storage_mm is not None:
        margins["voorraad"] = outcome.storage_mm - constraints.min_storage_mm
    if constraints.max_shortfall_mm is not None and outcome.shortfall_mm is not None:
        margins["tekort"] = constraints.max_shortfall_mm - outcome.shortfall_mm
    return margins


def _is_feasible(margins) -> bool:
    """Dezelfde toets als `_package_from`, zodat verkleinen niet buiten het haalbare valt."""
    return all(margin >= -FEASIBILITY_TOLERANCE for margin in margins.values())


def _minimise_priceless(
    state: PolderState, storm, actions, quantities, constraints, deficit
):
    """Verklein elke prijsloze maatregel tot de kleinste maatvoering die de eisen nog haalt.

    **Het probleem.** Een maatregel zonder prijs krijgt van de doelfunctie geen tegendruk:
    hij kost niets, dus niets duwt hem omlaag. Waar SLSQP hem laat staan hangt dan af van
    waar de zoektocht begon - bij nul blijft hij klein, bij de bovengrens
    (`optimise_mix.from_start(highs)`) blijft hij groot. Het pakket meldt dan "aanvoeren
    20 m3/s, prijs onbekend" terwijl de helft ook had gekund, en twee mixen die hetzelfde
    antwoord geven verschillen in de vierde decimaal van een maatregel die geen prijs heeft.
    Dat is ruis die als informatie wordt gepresenteerd, en juist `packages` en `near_optimal`
    horen navolgbaar te zijn.

    **De oplossing is lexicografisch.** Eerst de prijs, dan de prijsloze maatvoering: van
    alle pakketten die even duur zijn en de eisen halen, kiest hij het pakket dat het minste
    vraagt van wat geen prijs heeft. Dat is een tweede doelfunctie onder de eerste, en geen
    verzonnen prijs - de rangorde op kosten blijft precies zoals hij was.

    Zo wordt "hij doet niets, dus nul" het bijzondere geval van "zo klein mogelijk": haalt
    nul de eisen ook, dan valt de maatregel weg.

    **Ook op de onhaalbare tak**, en dat is niet vrijblijvend. Een onhaalbaar pakket komt in
    `packages` terecht, en juist daar hoort geen maatregel te staan die niets doet. Het
    criterium degradeert dan van "blijft haalbaar" naar "geen enkele marge gaat achteruit";
    zie `acceptable_at`. Stond die tak er niet, dan bleef een inerte maatregel op zijn
    zoekgrens staan zodra SLSQP daar was begonnen - en of dat gebeurt verschilt per platform,
    wat het een reproduceerbaarheidsprobleem maakt en niet alleen een cosmetisch.

    **Bisectie mag hier, en dat is niet vanzelfsprekend.** `sweep_measure` gebruikt met opzet
    een raster omdat de haalbaarheid in de maatvoering niet monotoon hoeft te zijn -
    vasthouden heeft een binnenoptimum. Maar hier komen alleen de PRIJSLOZE maatregelen
    langs, en die zijn per eis monotoon: peilopzet koopt voorraad en bufferdiepte en kost
    inundatiemarge, aanvoeren dekt tekort. Over het interval van nul tot de huidige waarde is
    er dus hoogstens een overgang, en die vindt bisectie exact. Vasthouden en bergen hebben
    een prijs en komen hier niet langs.
    """
    quantities = np.asarray(quantities, dtype=float).copy()
    margins = _margins_of(state, storm, actions, quantities, constraints, deficit)
    feasible = _is_feasible(margins)

    def margins_at(index, magnitude):
        trial = quantities.copy()
        trial[index] = magnitude
        return _margins_of(state, storm, actions, trial, constraints, deficit)

    def acceptable_at(index, magnitude) -> bool:
        """Mag deze maatvoering het antwoord zijn?

        Bij een haalbaar pakket is het criterium de haalbaarheid: kleiner mag zolang de eisen
        gehaald blijven. Bij een ONHAALBAAR pakket bestaat dat criterium niet - dan is niets
        haalbaar en zou elke bisectie op nul uitkomen, wat een onhaalbaar antwoord mooier
        voorstelt dan het is. Daar geldt het zwakkere criterium: kleiner mag alleen als geen
        enkele marge erop achteruitgaat. Een maatregel die niets doet valt dan alsnog weg -
        dat is de spookpakket-tak - en een maatregel die de eisen dichterbij brengt blijft
        staan op wat de zoeker vond.
        """
        trial = margins_at(index, magnitude)
        if feasible:
            return _is_feasible(trial)
        return all(trial[name] >= margins[name] - 1e-9 for name in margins)

    for index, action in enumerate(actions):
        magnitude = float(quantities[index])
        if magnitude <= 0.0 or action.at(magnitude).cost(state) is not None:
            continue
        if acceptable_at(index, 0.0):
            quantities[index] = 0.0
            continue
        if not feasible:
            # geen bisectie op een onhaalbaar pakket: het criterium hierboven is geen
            # eigenschap die met de maatvoering meebeweegt, dus er valt niets in te halveren
            continue
        # nul haalt het niet en de huidige waarde wel; de kleinste die nog haalt ligt
        # ertussen. `high` blijft per invariant haalbaar, dus afbreken is altijd veilig.
        low, high = 0.0, magnitude
        for _ in range(BISECTION_STEPS):
            middle = 0.5 * (low + high)
            if acceptable_at(index, middle):
                high = middle
            else:
                low = middle
        quantities[index] = high
    return quantities


def _package_from(
    state: PolderState, storm, actions, quantities, constraints, deficit=None
):
    highs = np.array([action.upper_bound(state) for action in actions])
    quantities = np.clip(quantities, 0.0, highs)
    quantities = np.where(quantities < NEGLIGIBLE_FRACTION * highs, 0.0, quantities)
    quantities = _minimise_priceless(
        state, storm, actions, quantities, constraints, deficit
    )

    after, dh_total, storage, cost, priceless, shortfall = outcome_of(
        state, storm, actions, quantities, deficit
    )
    margins = _margins_of(state, storm, actions, quantities, constraints, deficit)

    priced_band = cost_range_of(state, actions, quantities)
    replacement, replacement_band = replacement_cost_of(state, actions, quantities)
    eps = eps_of(state)
    feasible = _is_feasible(margins)
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
        shortfall_mm=None if shortfall is None else float(shortfall),
        binding=binding,
        priceless=priceless,
        cost_range=None if priceless else priced_band,
        priced_cost_range=priced_band,
        replacement_cost=replacement,
        replacement_cost_range=replacement_band,
    )


def optimise_mix(
    state: PolderState, storm, actions, constraints: Constraints, deficit=None
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
        return outcome_of(state, storm, actions, x, deficit).cost * COST_SCALE

    def inundation_margin(x):
        """>= 0 als de norm gehaald wordt."""
        return (
            constraints.max_dh_total_m
            - outcome_of(state, storm, actions, x, deficit).dh_total_m
        )

    def storage_margin(x):
        return (
            outcome_of(state, storm, actions, x, deficit).storage_mm
            - constraints.min_storage_mm
        )

    def shortfall_margin(x):
        """>= 0 als het tekort onder de eis blijft; de eis op de waterstand-as."""
        return (
            constraints.max_shortfall_mm
            - outcome_of(state, storm, actions, x, deficit).shortfall_mm
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
    if constraints.max_shortfall_mm is not None and deficit is not None:
        constraint_list.append(
            {
                "type": "ineq",
                "fun": shortfall_margin,
                "jac": lambda x: _finite_difference(shortfall_margin, x),
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
        return _package_from(state, storm, actions, solution.x, constraints, deficit)

    package = from_start(np.zeros(len(actions)))
    if package.feasible:
        return package
    # Als zelfs de bovengrens de eisen mist, kan deze mix het niet. Geen tweede zoektocht.
    at_bound = _package_from(state, storm, actions, highs, constraints, deficit)
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
    deficit=None,
) -> OptimizeResult:
    """Het goedkoopste pakket dat aan de eisen voldoet, over alle actiemixen.

    `max_mix_size` begrenst hoeveel maatregelen er tegelijk mogen worden ingezet. Standaard
    alle - dat is bij vijf acties eenendertig mixen en dus eenendertig SLSQP-runs. Wordt hij
    gezet, dan staat er in de uitvoer welke mixen niet zijn onderzocht; stil begrenzen leest
    als "alles gedekt" terwijl dat niet zo is.

    `deficit` is de exogene droogte (zie `supply.Deficit`), en hij is de tegenhanger van
    `storm`: de tweede belasting op dezelfde toestand. Hij is nodig zodra
    `constraints.max_shortfall_mm` is gezet, en zonder die eis verandert hij niets aan het
    antwoord.
    """
    if not constraints.any_set:
        raise ValueError(
            "geef minstens een eis; zonder eis is het goedkoopste pakket altijd niets doen"
        )
    if constraints.max_shortfall_mm is not None and deficit is None:
        raise ValueError(
            "max_shortfall_mm vraagt om een deficit; zonder droogte is er geen tekort "
            "om te meten"
        )

    largest = max_mix_size or len(actions)
    packages = []
    for size in range(1, largest + 1):
        for mix in combinations(actions, size):
            packages.append(optimise_mix(state, storm, mix, constraints, deficit))

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
        ranges=ranges_of(
            state, storm, actions, near_optimal, constraints, budget, deficit
        ),
    )


_AXES = {
    "inundatie": (lambda outcome: outcome.dh_total_m, -1),
    "voorraad": (lambda outcome: outcome.storage_mm, +1),
    "tekort": (lambda outcome: outcome.shortfall_mm, -1),
}
"""Per eis-as: hoe je hem uit een doorrekening leest, en welke richting beter is.

+1 betekent hoger is beter (voorraad), -1 lager is beter (waterstand, tekort). Dezelfde
drie assen als `Constraints`, onder de namen waaronder `_margins_of` ze rapporteert.
"""


def best_on_axis(
    state, storm, axis: str, actions=DEFAULT_ACTIONS, deficit=None
) -> float:
    """Het beste dat alle maatregelen SAMEN op deze ene as bereiken, los van de andere eisen.

    Dit is een andere vraag dan `optimize` beantwoordt. De gezamenlijke zoektocht
    optimaliseert kosten onder de eisen, en zodra die eisen samen onhaalbaar zijn, zegt
    het beste onderzochte punt niets over wat er op een losse as WEL kan - SLSQP
    minimaliseert daar geen overtreding. Deze doorrekening doet dat wel: geen kosten, geen
    andere eisen, alleen deze as zo ver mogelijk de goede kant op. Daarmee is het antwoord
    een echte grens: verder dan dit komt het met deze vijf maatregelen niet.

    Drie startpunten om dezelfde reden als `optimise_mix`: het landschap heeft vlakke
    stukken en een enkele start kan daar blijven liggen.
    """
    reader, direction = _AXES[axis]
    highs = np.array([action.upper_bound(state) for action in actions])

    def objective(x):
        return -direction * reader(outcome_of(state, storm, actions, x, deficit))

    best = None
    for start in (np.zeros_like(highs), highs * 0.5, highs.copy()):
        answer = minimize(
            objective,
            start,
            method="SLSQP",
            bounds=[(0.0, high) for high in highs],
            options={"maxiter": 200, "ftol": 1e-9},
        )
        value = reader(outcome_of(state, storm, actions, answer.x, deficit))
        if best is None or direction * value > direction * best:
            best = value
    return float(best)


def can_improve_a_requirement(
    state, storm, actions, quantities, constraints, index, deficit=None
) -> bool:
    """Verbetert MEER van deze ene maatregel een gestelde eis, gemeten aan dit punt?

    Dit is het onderscheid dat een rol `absent` alleen niet draagt: een maatregel kan
    ontbreken omdat hij niets aan de gestelde eisen doet, of omdat hij wel bijdraagt maar
    niet binnen de prijsband van het beste pakket past. Voor een bestuurder is dat het
    verschil tussen een maatregel die nooit meedeed en een die afviel op prijs.

    Gemeten met een eindige stap vanaf het aangeboden punt, op alleen de marges van de
    eisen die werkelijk zijn gesteld. Aanvoeren op de statische voorraadeis geeft exact
    nul en telt dus niet; peilopzet op alleen de inundatie-eis maakt de marge kleiner en
    telt ook niet.
    """
    step = max(actions[index].upper_bound(state) * 1e-3, 1e-9)
    base = _margins_of(state, storm, actions, quantities, constraints, deficit)
    bumped = list(quantities)
    bumped[index] = float(bumped[index]) + step
    after = _margins_of(state, storm, actions, bumped, constraints, deficit)
    return any(after[name] > base[name] + 1e-12 for name in base)


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

    De band komt uit `priced_cost_range` en dus over het deel dat WEL een prijs heeft: een
    prijsloze maatregel ernaast laat de epsilon staan, want over het geprijsde deel weten we
    nog steeds wat we weten. Nul is hij alleen zodra er in het hele pakket niets is dat een
    prijs heeft - dan is er geen band om ergens om te leggen. Zie `Package.cost_range`, dat
    juist wel op `None` gaat zodra er een prijsloze maatregel in zit, en `switch_price_of`.
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
    state: PolderState,
    storm,
    actions,
    quantities,
    index,
    constraints,
    budget,
    deficit=None,
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
        outcome = outcome_of(state, storm, actions, trial, deficit)
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
        if (
            constraints.max_shortfall_mm is not None
            and outcome.shortfall_mm is not None
            and outcome.shortfall_mm
            > constraints.max_shortfall_mm + FEASIBILITY_TOLERANCE
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
    state: PolderState, storm, actions, near_optimal, constraints, budget, deficit=None
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
                state, storm, actions, quantities, index, constraints, budget, deficit
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
    deficit=None,
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

    **Deze functie neemt aan dat de prijs LINEAIR is in de maatvoering, en voor drooglegging
    is dat aantoonbaar de verkeerde vorm.** De vastgestelde Nederlandse methodiek - zie
    `ValueCurve` en `DROOGLEGGING_VALUE_VEEN` - heeft een plateau boven ongeveer 90 cm
    drooglegging, een klif op 30 cm, en wettelijk verplichte discrete stappen. De marginale
    prijs varieert daarin van nul tot 900 euro per hectare per centimeter, en welk stuk geldt
    hangt af van de drooglegging van de polder - een grootheid die `PolderState` NIET heeft.

    Wat deze functie dus levert is de prijs van een lineaire proxy, en die is bruikbaar als
    ordegrootte om tegen de echte curve te houden: valt de marginale prijs in de relevante band
    boven het kantelpunt, dan verandert het antwoord. Zie
    `test_the_documented_curve_puts_every_band_above_the_first_switch_point`, die dat voor de
    hele gedocumenteerde curve narekent. Wat hij niet levert is "de" prijs waarbij het omslaat,
    want die bestaat niet als een getal.

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
            state,
            storm,
            constraints,
            actions=tuple(priced),
            max_mix_size=max_mix_size,
            deficit=deficit,
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
