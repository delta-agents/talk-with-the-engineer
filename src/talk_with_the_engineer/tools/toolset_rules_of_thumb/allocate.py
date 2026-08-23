"""Wie krijgt wat als het water op is: de verdringingsreeks op een boom.

Aan de natte kant is de koppeling lokaal - mijn uitstroom is jouw aanvoer, en een pass in
topologische orde lost het op. Aan de droge kant is hij **globaal**: alle afnemers trekken
uit dezelfde eindige bron en die staan niet achter elkaar maar naast elkaar. Er bestaat geen
doorloopvolgorde die dat oplost; je moet verdelen. Daarom hangt dit naast `simulate_network`
en niet erin. Zie PLAN_UITWISSELING_EN_NETWERK.md Sec. 6.4.

**En daarom hoeft er toch geen LP in.** Sec. 6.4 zet er een lineair programma neer, en dat
is de algemene oplossing - maar niet de onze. `SystemState` staat precies één uitgaande
verbinding per knoop toe, en `Connection` draagt beide capaciteiten naar dezelfde `to`. Op de
droge kant heeft elke afnemer dus precies **één bron** en precies **één pad** daarheen. Dan
is er niets te routeren, en dan is de toewijzing een transportprobleem op een boom met een
gesloten vorm: twee gevectoriseerde passes per categorie.

Dat is geen gemakzucht maar de literatuur. Danna e.a. (*Upward Max Min Fairness*, IEEE
INFOCOM 2012) stellen het expliciet: bij één pad per afnemer geeft water-filling de max-min
fair oplossing, en bij MEERDERE paden is er geen combinatorisch algoritme bekend en moet je
terugvallen op een reeks LP's. De scheidslijn is dus **fan-out en niet diepte**: diepte 3 à 4
kost ons niets, fan-out 2 kost ons de hele gesloten vorm. Le Boudec (EPFL, 2021) Thm 1.2.2
t/m 1.2.4 geeft er de uniciteit bij.

Winst boven een solver, en het is niet de snelheid: **geen solver in het pad betekent geen
platformverschil.** Een sort en een cumsum geven per constructie hetzelfde antwoord op Linux
en macOS; een LP-solver geeft dat bij hoop. Dat is invariant I6 uit BOUW_WP13_WP15.md, en het
is dezelfde les als issue #30 - daar was het SLSQP die op twee platforms een ander punt koos.

**Wat de wet hier zegt, en dat is meer dan verwacht.** Het Landelijk draaiboek
waterverdeling en droogte (29-01-2026, tabel 3.1) zegt op grond van artikel 3.14 Bkl:

    "Binnen de categorieën 1 en 2 is sprake van een prioriteitsvolgorde. Binnen de
     categorieën 3 en 4 vindt onderlinge prioritering plaats op basis van minimalisatie
     van de economische maatschappelijke schade."

En de Handleiding verdringingsreeks (v2, 26-03-2020): "Nadere prioritering tussen categorie
3 en categorie 4 is niet mogelijk."

Drie dingen volgen daaruit, en ze zitten in de code:

1. Lexicografisch tussen de schillen is **wettelijk**, en de schillen zijn ondoordringbaar.
   Dat sluit "één LP met grote gewichten" uit: dat lekt altijd een beetje over de
   categoriegrens, en dat mag hier niet.
2. Binnen categorie 3 en 4 noemt de wet een criterium, en dat is `min som(w_i * tekort_i)` -
   de **gewogen** vorm. Niet gelijk tekort en niet maximin.
3. Gelijk tekort is dus een **proxy** voor onbekende schadefuncties. Verdedigbaar, want wij
   kennen die functies niet, maar het is niet wat de wet vraagt en het hoort zo gemeld te
   worden. Zie `WithinShellRule`.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np

from talk_with_the_engineer.models.modelset_rules_of_thumb.results import MeasureRole
from talk_with_the_engineer.models.modelset_rules_of_thumb.system import (
    BOUNDARY,
    SystemState,
)

TINY = 1e-15
"""Deler-beveiliging. Geen tolerantie: puur om 0/0 te vermijden in een gevectoriseerde tak."""

RELATIVE_TOLERANCE = 1e-9
"""Wanneer een keel vol is, relatief aan de volumes die er in omgaan.

**Bewust relatief**, en dat is met schade geleerd. Met een absolute `1e-15` op volumes van
enkele miljoenen m3 werd een inlaat die net was leeggetrokken NIET als verzadigd herkend: de
restterm na aftrek is bij die orde van grootte zo'n 1e-10, en dus duizenden keren groter dan
de drempel. Water-filling bevroor daardoor niemand, stopte na één ronde, en gaf tot 34 %
minder weg dan er kon - stil, en alleen zichtbaar tegen een LP.

Dat is precies dezelfde fout als `binding` in de pakketzoeker, die 1 mm op de stand en 1
micrometer op de voorraad betekende omdat één getal twee eenheden moest dekken. Een
tolerantie hoort bij de grootheid die hij toetst.
"""


class WithinShellRule(str, Enum):
    """Hoe er binnen één categorie wordt verdeeld als er niet genoeg is.

    Lexicografisch tussen de schillen is niet één van de opties - dat is de wettelijke
    buitenlaag en die staat altijd aan. Wat hier gekozen wordt, is de binnenlaag, en die is
    nodig: met één bron en drie afnemers in categorie 1 wier som het aanbod overschrijdt,
    legt de reeks de verdeling **niet** vast. Een lexicografische ordening zonder
    binnen-de-schil-regel is dus geen antwoord maar een onderbepaald stelsel.
    """

    PROPORTIONAL = "proportional"
    """Gelijk tekort: iedereen in de schil dezelfde dekkingsfractie.

    Een PROXY voor de wettelijke schademinimalisatie, en zo hoort hij gemeld te worden. Hij
    is wat WEAP zijn Equity Groups noemt en wat Ribasim als fairness-term toevoegt, dus hij
    is gangbaar - maar hij is niet wat art. 3.14 Bkl vraagt zodra de schadefuncties
    verschillen. Wij kennen die functies niet; dat is de reden, en niet dat dit de juiste
    vorm is.
    """

    WEIGHTED = "weighted"
    """Schademinimalisatie: `min som(w_i * tekort_i)`, greedy op aflopend gewicht.

    **Dit is wat de wet vraagt** binnen categorie 3 en 4. Nog niet gebouwd, en de reden is
    niet technisch: de gewichten zijn de marginale schade per m3 en die hebben wij niet. Een
    gewicht verzinnen is hier hetzelfde als een prijs verzinnen voor peilopzet - zie issue
    #30. Zodra ze er zijn is de implementatie Edmonds' greedy op een polymatroid (Schrijver
    hfst. 44, Thm 44.3), met één bewijsverplichting: dat de laminaire familie van deelbomen
    werkelijk een polymatroid oplevert. Zie BOUW_WP13_WP15.md WP14.0 en WP14.3.
    """

    MAXIMIN = "maximin"
    """Maximaliseer de slechtst bedeelde: capped water-filling.

    De meest egalitaire lezing, en de oplossing is UNIEK (Le Boudec Thm 1.2.2). Niet
    wettelijk voorgeschreven, maar de nuttigste tweede kolom: samen met gelijk tekort geeft
    hij een BAND om het antwoord dat de wet eigenlijk vraagt, zonder dat we een gewicht
    verzinnen. Nog niet gebouwd; zie WP14.3.
    """


@dataclass(frozen=True)
class AllocationResult:
    """Wie wat krijgt, en wat er bindt.

    Geen rij per knoop naar buiten - dezelfde les als `RegionOutput`. Bij vijftig afnemers is
    een rij per afnemer nog leesbaar en bij duizend niet, en de vraag is bijna nooit "geef me
    alle volumes" maar "wie valt af, en vanaf wanneer".
    """

    granted_m3: np.ndarray
    demand_m3: np.ndarray
    categories: np.ndarray
    available_m3: float
    rule: WithinShellRule

    @property
    def shortfall_m3(self) -> np.ndarray:
        return self.demand_m3 - self.granted_m3

    @property
    def coverage(self) -> np.ndarray:
        """De dekkingsfractie per afnemer; 1,0 als er geen vraag is."""
        return np.where(
            self.demand_m3 > TINY,
            self.granted_m3 / np.maximum(self.demand_m3, TINY),
            1.0,
        )

    def coverage_of_category(self, category: int) -> float:
        """De dekkingsfractie van een hele categorie."""
        selection = self.categories == category
        demand = self.demand_m3[selection].sum()
        if demand <= TINY:
            return 1.0
        return float(self.granted_m3[selection].sum() / demand)

    @property
    def binding_category(self) -> int | None:
        """De laagste categorie die niet volledig is gedekt; `None` als alles gedekt is.

        Dit is de uitlezing die een waterschap nodig heeft: niet de volumes maar "vanaf hier
        valt het af". Dezelfde vorm als `binding_node` op de natte kant.
        """
        for category in sorted(set(int(c) for c in self.categories)):
            if self.coverage_of_category(category) < 1.0 - 1e-9:
                return category
        return None

    def role_of(self, category: int) -> MeasureRole:
        """De rol van een categorie in deze toewijzing.

        Hetzelfde `MeasureRole` als de pakketzoeker gebruikt, en dat is geen hergebruik om
        het hergebruik: het is dezelfde uitspraak. `FORCED` betekent daar "zit in elk pakket
        in het gebied" en hier "krijgt zijn volle vraag"; `ABSENT` daar "draagt niet bij" en
        hier "krijgt niets". Eén vocabulaire voor twee operatoren - zie issue #30 en #31.
        """
        coverage = self.coverage_of_category(category)
        if coverage >= 1.0 - 1e-9:
            return MeasureRole.FORCED
        if coverage <= 1e-9:
            return MeasureRole.ABSENT
        return MeasureRole.OPTIONAL


def _subtree_sum(system: SystemState, value, levels) -> np.ndarray:
    """Per knoop de som van `value` over hemzelf en alles wat bovenstrooms aan hem hangt.

    Dat is precies wat er door de inlaat van die knoop heen moet, want alle afnemers achter
    hem trekken door zijn keel. Één pass van de bladeren naar de rand, gevectoriseerd over de
    knoop-as met een scatter-add - dezelfde richting en dezelfde vorm als `_forward_pass` op
    de natte kant.

    De invariant van `topological_levels` maakt dit exact: elke voorganger ligt op een strikt
    kleinere diepte, dus als we een knoop verwerken zijn al zijn kinderen al bij hem opgeteld.
    """
    total = np.asarray(value, dtype=float).copy()
    for group in levels:
        parents = system.downstream[group]
        receiving = parents != BOUNDARY
        if receiving.any():
            np.add.at(total, parents[receiving], total[group][receiving])
    return total


def _blocked_by(
    system: SystemState, saturated, levels, source_empty: bool
) -> np.ndarray:
    """Welke knopen achter een verzadigde klem zitten, van de rand naar de bladeren.

    Een afnemer kan niets meer krijgen zodra er ergens op zijn pad naar de bron geen ruimte
    meer is - zijn eigen inlaat, die van de boezem, of de bron zelf. Omdat elke afnemer
    precies één pad heeft, is dat een simpele doorgifte omlaag: geblokkeerd als je zelf
    verzadigd bent of je ouder geblokkeerd is.

    Dit is de stap die water-filling van een enkele deling onderscheidt. Wie tegen zijn klem
    aan zit wordt bevroren, en het water dat daardoor vrijkomt gaat naar de rest in plaats
    van verloren te gaan.
    """
    blocked = np.asarray(saturated, dtype=bool).copy()
    if source_empty:
        blocked |= system.downstream == BOUNDARY
    for group in reversed(levels):
        parents = system.downstream[group]
        receiving = parents != BOUNDARY
        if not receiving.any():
            continue
        children = group[receiving]
        blocked[children] |= blocked[parents[receiving]]
    return blocked


def _fill_shell(system, demand_m3, capacity_m3, available_m3, levels):
    """Verdeel binnen één categorie: gelijke dekking waar dat kan, capped water-filling.

    Naïef proportioneel verdelen is hier niet goed genoeg, en de test wees dat aan. Als één
    afnemer tegen zijn eigen inlaat aan loopt, is zijn dekking lager dan die van de anderen -
    en dan is "iedereen dezelfde fractie" onwaar zolang je het water dat hij niet kan opnemen
    niet aan de rest geeft. Vandaar de ronden:

    1. bepaal de grootste fractie `f` van de resterende vraag die overal doorheen past. Dat
       is een gesloten vorm en geen bisectie: `f` is het minimum van `voorraad / totale
       restvraag` en, per knoop, `restcapaciteit / restvraag in zijn deelboom`;
    2. ken `f` maal de restvraag toe, en trek af wat er door elke inlaat ging;
    3. bevries wie achter een verzadigde klem zit, en herhaal voor de rest.

    Dat is progressive filling (Bertsekas & Gallager, Data Networks 2e ed., hfst. 6 §6.5.2,
    p. 524-530), en de uitkomst is uniek (Le Boudec Thm 1.2.2). Ten hoogste één ronde per
    klem, en elke ronde is twee gevectoriseerde passes.

    Let op wat `f` weegt: de RESTVRAAG, dus iedereen krijgt dezelfde FRACTIE van zijn vraag.
    Dat is gelijk tekort. Wil je maximin - maximaliseer de kleinste absolute toewijzing - dan
    is het dezelfde lus met een andere weegvector, en dat is de reden dat WP14.3 goedkoop is.

    Levert naast de toewijzing en de doorvoer per knoop ook het cumulatieve volume aan de
    RAND na elke ronde. Dat derde is geen debug-informatie maar de kern van het theta-plaatje:
    elke ronde eindigt doordat er precies één klem verzadigt, en dus is elk van die volumes
    een knikpunt. Zie `theta_breakpoints`.
    """
    demand_m3 = np.asarray(demand_m3, dtype=float)
    granted = np.zeros_like(demand_m3)
    capacity = np.asarray(capacity_m3, dtype=float).copy()
    left = float(available_m3)
    frozen = np.zeros(system.size, dtype=bool)
    roots = system.downstream == BOUNDARY
    consumed_at_root = []

    # de drempel hoort bij de volumes die hier omgaan; zie RELATIVE_TOLERANCE
    scale = max(float(demand_m3.sum()), 1.0)
    tolerance = RELATIVE_TOLERANCE * scale

    for _ in range(system.size + 1):
        outstanding = np.maximum(np.where(~frozen, demand_m3 - granted, 0.0), 0.0)
        if outstanding.sum() <= tolerance or left <= tolerance:
            break

        needed = _subtree_sum(system, outstanding, levels)
        # de grootste fractie die zowel de bron als elke keel op het pad toestaat
        fraction = 1.0
        root_need = needed[roots].sum()
        if root_need > tolerance:
            fraction = min(fraction, left / root_need)
        binding = needed > tolerance
        if binding.any():
            fraction = min(fraction, float((capacity[binding] / needed[binding]).min()))
        fraction = min(max(fraction, 0.0), 1.0)

        add = fraction * outstanding
        granted += add
        through = _subtree_sum(system, add, levels)
        capacity = np.maximum(capacity - through, 0.0)
        left = max(left - float(through[roots].sum()), 0.0)
        consumed_at_root.append(
            float(_subtree_sum(system, granted, levels)[roots].sum())
        )

        if fraction >= 1.0 - RELATIVE_TOLERANCE:
            break  # alle resterende vraag is gedekt
        # bevries wie niet verder kan; de rest gaat een ronde verder
        still_wanted = _subtree_sum(
            system, np.maximum(np.where(~frozen, demand_m3 - granted, 0.0), 0.0), levels
        )
        saturated = (capacity <= tolerance) & (still_wanted > tolerance)
        newly = _blocked_by(system, saturated, levels, left <= tolerance)
        if not (newly & ~frozen).any():
            break  # niets nieuws bevroren: verder komen we niet
        frozen |= newly

    return granted, _subtree_sum(system, granted, levels), tuple(consumed_at_root)


def allocate(
    system: SystemState,
    demand_m3,
    categories,
    available_m3: float,
    duration_days: float,
    rule: WithinShellRule = WithinShellRule.PROPORTIONAL,
) -> AllocationResult:
    """Verdeel een eindige bron over de afnemers, lexicografisch per categorie.

    Vier categorieën geeft vier keer een water-filling, en dat is de hele berekening - geen
    solver, geen iteratie over droogtejaren, geen tweede netwerkcode. Per categorie verdeelt
    `_fill_shell` wat er nog is, en daarna gaat wat er door een inlaat ging van die capaciteit
    af en wat de rand verliet van de voorraad - zodat de volgende categorie ziet wat er over
    is.

    Dat laatste is waar de ondoordringbaarheid van de schillen zit: categorie 4 kan de
    capaciteit die categorie 1 gebruikte niet terugvragen, en geen gewicht kan daar tegenop.
    Dat is geen modelkeuze maar de Handleiding verdringingsreeks: "nadere prioritering tussen
    categorie 3 en categorie 4 is niet mogelijk".

    `duration_days` zet de inlaatcapaciteiten (m3/s) om in volumes over de periode. De
    aanvoerkant rekent in volumes en niet in debieten, want dat is de grootheid waarin een
    bron eindig is: 0,45 l/s/ha klinkt als een pompje, 4,68 miljoen m3 in een maand is een
    vraag aan het regionale systeem.
    """
    demand_m3 = np.asarray(demand_m3, dtype=float)
    categories = np.asarray(categories)
    if demand_m3.shape != (system.size,) or categories.shape != (system.size,):
        raise ValueError("vraag en categorie horen een waarde per knoop te hebben")
    if rule is not WithinShellRule.PROPORTIONAL:
        raise NotImplementedError(
            f"de binnen-de-schil-regel {rule.value!r} is nog niet gebouwd; "
            "zie BOUW_WP13_WP15.md WP14.3"
        )

    seconds = duration_days * 86_400.0
    capacity_m3 = system.capacity_in_m3_per_sec.astype(float) * seconds
    levels = system.topological_levels()

    granted = np.zeros(system.size)
    remaining = float(available_m3)
    for category in sorted(set(int(c) for c in categories)):
        own = np.where(categories == category, demand_m3, 0.0)
        if own.sum() <= TINY:
            continue
        round_granted, through, _events = _fill_shell(
            system, own, capacity_m3, remaining, levels
        )
        granted += round_granted
        # wat er door een inlaat ging is voor de volgende categorie niet meer beschikbaar
        capacity_m3 = np.maximum(capacity_m3 - through, 0.0)
        root = system.downstream == BOUNDARY
        remaining = max(remaining - float(through[root].sum()), 0.0)

    return AllocationResult(
        granted_m3=granted,
        demand_m3=demand_m3,
        categories=categories,
        available_m3=float(available_m3),
        rule=rule,
    )


@dataclass(frozen=True)
class ThetaRegime:
    """Eén stuk van de theta-trap: een bereik van droogte met één regime erin.

    Binnen zo'n stuk is de toewijzing LINEAIR in theta - er verandert niets aan welke klem
    bindt, alleen aan hoeveel er door gaat. De knikpunten ertussen zijn de momenten waarop
    een keel verzadigt of een categorie vol raakt.
    """

    theta_low: float
    theta_high: float
    coverage: dict[int, float]
    """De dekkingsfractie per categorie aan de BOVENkant van dit stuk."""
    binding_category: int | None


def theta_breakpoints(
    system: SystemState,
    demand_m3,
    categories,
    duration_days: float,
    rule: WithinShellRule = WithinShellRule.PROPORTIONAL,
) -> tuple[float, ...]:
    """De theta-waarden waar het regime omslaat, exact en zonder te sweepen.

    `theta` is het beschikbare volume als fractie van de totale vraag: 1 betekent dat
    iedereen kan, 0 dat er niets is.

    **Dit is het antwoord op "sweep of mpLP", en het is geen van beide.** Gal & Nedoma (1972)
    zeggen dat de optimale toewijzing van een LP stuksgewijs lineair is in zijn parameters en
    dat het parameterbereik in *critical regions* uiteenvalt. Dat is waar, en de gebruikelijke
    weg is die regio's construeren met multiparametrisch LP. Bij ons is dat een omweg: de
    water-filling **produceert** ze al. Elke ronde eindigt doordat er precies één klem
    verzadigt, en het cumulatieve volume op dat moment is per definitie een knikpunt. De
    regio's zijn dus een bijproduct van het antwoord in plaats van een aparte berekening.

    Daarom geen dichte sweep als antwoord. Wel als **test**: een sweep over duizend punten
    moet exact op de stuksgewijs-lineaire reconstructie liggen, en dat is te toetsen. Zie
    `test_the_breakpoints_are_analytic`.

    De knikpunten komen uit twee bronnen, en ze horen bij elkaar:

    * **binnen** een categorie: elke ronde van de water-filling, want daar verzadigt een keel;
    * **tussen** categorieën: het volume waarop een categorie volledig gedekt is en de
      volgende aan de beurt komt. Dat is de lexicografische overdracht, en op de trap is het
      de scherpste knik - daar valt de volgende categorie in één keer aan of af.

    Kosten: één water-filling per categorie met oneindige voorraad. Vier categorieën, dus
    dezelfde orde als één toewijzing.
    """
    demand_m3 = np.asarray(demand_m3, dtype=float)
    categories = np.asarray(categories)
    if rule is not WithinShellRule.PROPORTIONAL:
        raise NotImplementedError(
            f"de binnen-de-schil-regel {rule.value!r} is nog niet gebouwd; "
            "zie BOUW_WP13_WP15.md WP14.3"
        )

    total_demand = float(demand_m3.sum())
    if total_demand <= TINY:
        return (0.0, 1.0)

    seconds = duration_days * 86_400.0
    capacity_m3 = system.capacity_in_m3_per_sec.astype(float) * seconds
    levels = system.topological_levels()
    roots = system.downstream == BOUNDARY

    volumes = [0.0]
    offset = 0.0
    for category in sorted(set(int(c) for c in categories)):
        own = np.where(categories == category, demand_m3, 0.0)
        if own.sum() <= TINY:
            continue
        # oneindige voorraad: we willen weten WAAR de klemmen liggen, niet hoe droog het is
        _granted, through, events = _fill_shell(
            system, own, capacity_m3, float("inf"), levels
        )
        volumes.extend(offset + volume for volume in events)
        offset += float(through[roots].sum())
        capacity_m3 = np.maximum(capacity_m3 - through, 0.0)

    # naar theta, ontdubbeld, en 1,0 erbij zodat de trap tot het volle aanbod loopt
    scale = RELATIVE_TOLERANCE
    thetas = sorted({min(volume / total_demand, 1.0) for volume in volumes} | {1.0})
    deduped = [thetas[0]]
    for theta in thetas[1:]:
        if theta - deduped[-1] > scale:
            deduped.append(theta)
    return tuple(deduped)


def theta_table(
    system: SystemState,
    demand_m3,
    categories,
    duration_days: float,
    rule: WithinShellRule = WithinShellRule.PROPORTIONAL,
) -> tuple[ThetaRegime, ...]:
    """De trap zelf: per stuk droogte wie er hoeveel krijgt.

    Dit is de uitlezing die een waterschap wil - "bij 40 % aanbod is landbouw in elke vorm
    nul en drinkwater in elke vorm vol; de middenmoot verschilt" - en niet een lijst volumes.
    Geen twintig KNMI-jaren nodig: theta is de interne as, en een echte droogtereeks kan hem
    later voeden in plaats van hem te vervangen.
    """
    thetas = theta_breakpoints(system, demand_m3, categories, duration_days, rule)
    total_demand = float(np.asarray(demand_m3, dtype=float).sum())
    present = sorted(set(int(c) for c in np.asarray(categories)))

    regimes = []
    for low, high in zip(thetas, thetas[1:]):
        result = allocate(
            system, demand_m3, categories, high * total_demand, duration_days, rule
        )
        regimes.append(
            ThetaRegime(
                theta_low=low,
                theta_high=high,
                coverage={
                    category: result.coverage_of_category(category)
                    for category in present
                },
                binding_category=result.binding_category,
            )
        )
    return tuple(regimes)
