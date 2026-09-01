"""Uitkomst van een inverse berekening: hoeveel maatregel is er nodig?

De statusvelden bestaan omdat er een haalbaar bereik is. Voorheen werd met `np.interp`
geinterpoleerd, en die klemt stil op de randen: een doel onder het haalbare leverde
"0 ha nodig" op en een doel erboven "100 %", zonder enige melding.
"""

from enum import Enum
from math import floor, isfinite, log10
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, model_serializer

from talk_with_the_engineer.models.base import EngineerOutputModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    Assumption,
    ModelCaveat,
    Sensitivity,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState


SIGNIFICANT_DIGITS = 4
"""Aantal significante cijfers in de tooluitvoer.

Deze tools zijn vuistregels, en de oplosser is een bisectie: die levert zestien cijfers
waarvan er hooguit drie iets betekenen. Ze allemaal doorgeven suggereert precisie die er
niet is en kost de lezer - mens of model - alleen maar moeite. Vier cijfers houdt 1,806 m
op millimeters, 111,2 ha op are en 15,01 miljoen euro op tienduizend euro nauwkeurig.

Significante cijfers en geen vast aantal decimalen, want de uitvoer loopt van 0,086 m tot
383 miljoen euro; een vaste komma is voor het ene eind onzin en voor het andere ruis.
Alleen de uitvoer wordt afgerond - de rekenkern rekent onverkort door, en de gouden
regressietest tegen het rekenblad staat nog steeds op 1e-12.
"""


def round_significant(value: float, digits: int = SIGNIFICANT_DIGITS) -> float:
    """Rond af op `digits` significante cijfers; 0 en niet-eindige waarden blijven zoals ze zijn."""
    if value == 0 or not isfinite(value):
        return value
    return round(value, -int(floor(log10(abs(value)))) + (digits - 1))


def round_floats(value: Any) -> Any:
    """Rond elke float in een geneste structuur af. Ints blijven int: dagen zijn dagen."""
    if isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        return round_significant(value)
    if isinstance(value, dict):
        return {k: round_floats(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(round_floats(v) for v in value)
    return value


class SolveStatus(str, Enum):
    EXACT = "exact"
    """Het doel is haalbaar en de maatvoering is bepaald."""

    NO_MEASURE_NEEDED = "no_measure_needed"
    """De waterstand blijft al zonder maatregel onder het doel."""

    ACTION_INFEASIBLE = "action_infeasible"
    """Deze maatregel kan het doel niet halen. Een andere, of een combinatie, misschien wel.

    Het onderscheid met `problem_infeasible` bestaat omdat een agent anders uit een
    antwoord over een losse maatregel concludeert dat het probleem onoplosbaar is. Bergen
    kan de inundatienorm niet halen en bergen plus peilopzet wel; dat is precies het
    verschil tussen doorzoeken en opgeven. Heette eerder `infeasible`, wat die twee
    dingen niet uit elkaar hield.
    """

    PROBLEM_INFEASIBLE = "problem_infeasible"
    """Geen enkel pakket kan het doel halen.

    Wordt door `solve` nooit geleverd - die kijkt naar een maatregel per keer. Bestaat voor
    de pakketzoeker uit WP11, en staat hier zodat het onderscheid nu al in het schema staat
    en een agent er niet later door verrast wordt.
    """


class LimitReason(str, Enum):
    NONE = "none"
    MEASURE_OPTIMUM = "measure_optimum"
    """De maatregel heeft een optimum; verder uitbreiden maakt het slechter."""

    PHYSICAL_UPPER_BOUND = "physical_upper_bound"
    """De maatvoering loopt tegen een fysieke grens aan."""

    PAST_OPTIMUM = "past_optimum"
    """De opgegeven maatvoering ligt VOORBIJ het optimum van de maatregel.

    Alleen bij een voorwaartse vraag, en alleen bij een binnenoptimum. Het antwoord is dan
    nog steeds exact - de vraag was "wat doet deze maatvoering", en dat is precies wat er
    staat - maar het is duurder EN slechter dan een kleinere maatvoering. Op de
    referentiepolder betaalt 3800 ha 44 % meer dan 2645 ha voor een 5 cm hogere stijging.

    Dat was uitsluitend af te leiden uit `magnitude_optimum_kind: "interior"` naast
    `magnitude_at_optimum_ha` < `measure.after` - twee velden vergelijken die nergens als
    paar worden geintroduceerd. En juist het binnenoptimum bij vasthouden is het meest
    contra-intuitieve resultaat dat dit model produceert, dus daar is een expliciete vlag
    het meeste waard.
    """


class MeasureRole(str, Enum):
    """Wat een maatregel doet in het BIJNA-OPTIMALE GEBIED, niet in één pakket.

    Een optimum is alleen optimaal voor wat er gemodelleerd is. Wat een beslisser daarnaast
    heeft - draagvlak, uitvoerbaarheid, een prijs die eigenlijk een trap is, een buur die we
    nog niet kennen - leeft náást dat punt, en het enige wat wij daarover kunnen zeggen is
    hoeveel ruimte er is. Deze drie waarden zijn die uitspraak.

    Bewust op de RANGORDE en niet op de maatvoering. WP12 mat dat de rangorde van bergen en
    afvoeren in 0 van 162 invoercombinaties omdraait terwijl de hectares een factor honderd
    bewegen; de robuuste uitspraak is dus "welke maatregel", niet "hoeveel".

    Wordt gedeeld door de pakketzoeker (een maatregel in een pakket) en door de toewijzing op
    de droge kant (een afnemer in een verdeling): zelfde discipline, andere operator.
    """

    FORCED = "forced"
    """Zit in ELK pakket dat binnen de marge even goed is. Hier is geen keuze."""

    OPTIONAL = "optional"
    """Zit in sommige en niet in andere. Hier is wél een keuze, en die is niet van ons."""

    ABSENT = "absent"
    """Zit in geen enkel pakket in het gebied.

    Zonder reden erbij, want die is uit het gebied niet af te lezen: een maatregel kan
    ontbreken omdat hij niet bijdraagt aan de gestelde eisen, of omdat elke inzet buiten de
    prijsband van het beste pakket valt - en bij een prijsloos beste pakket is die band nul
    breed, waardoor elke geprijsde maatregel erbuiten valt hoe nuttig hij ook is.
    """


class OptimumKind(str, Enum):
    """Wat voor punt `magnitude_at_optimum` is.

    De naam "optimum" suggereert bij elke maatregel hetzelfde, en dat klopt niet. Bij
    vasthouden is het een echt optimum: verder uitbreiden maakt de waterstand weer hoger.
    Bij afvoeren is het het punt waar de stijging zijn ondergrens raakt en daarna vlak
    blijft; meer pompcapaciteit is daar verspilling, maar niet schadelijk. Zonder dit
    onderscheid leest een lezer - mens of model - "meer dan 11,88 m3/s is contraproductief",
    en dat staat er niet.
    """

    INTERIOR = "interior"
    """Voorbij dit punt wordt de waterstandstijging weer groter."""

    PLATEAU = "plateau"
    """Voorbij dit punt verandert de waterstandstijging niet meer.

    De maatregel heeft zijn eigen ondergrens bereikt: bij afvoeren is de stijging niet
    verder te verlagen omdat er niets meer te verlagen valt.
    """

    SATURATED = "saturated"
    """Voorbij dit punt verandert er niets meer, maar door een ANDERE grootheid.

    Het verschil met `plateau` is wie de klem is. Bij voorbemaling stopt de winst op
    10,5 cm niet omdat de waterstand niet lager kan, maar omdat het gemaal niet sneller
    leegmaalt. Meer marge *afspreken* helpt dan niet; een groter gemaal wel. Dat is een
    ander advies dan "hier is niets meer te halen", en het is uit het getal alleen niet
    af te lezen.
    """

    UPPER_BOUND = "upper_bound"
    """De maatvoering zit tegen zijn fysieke bovengrens; groter kan niet."""


# Waarom dit blok bestaat. "Geen prijs" is niet "gratis", en het verschil bepaalt de
# uitkomst: zolang de pakketzoeker `None` als nul behandelde, kocht peilopzet
# inundatiemarge zonder tegenprijs en verschoof het goedkoopste pakket van bergen naar
# afvoeren. Zie `PeilopzetAction` en issue #30. Dezelfde stilte bestond aan de toolkant -
# een peilmarge van 30 cm brengt de benodigde berging van 68 naar 38 ha en de kosten van
# 9,2 naar 5,1 miljoen euro, en er stond niets in het antwoord dat eraan herinnerde dat
# die 30 cm iets kost.
#
# De docstring hieronder houdt dat verhaal niet vast: hij komt in het UITVOERSCHEMA
# terecht en wordt gelezen door een agent die nog geen antwoord heeft gezien.
class PricelessPost(BaseModel):
    """Een post in het antwoord die geen bedrag heeft, maar wel een prijs.

    Peilopzet, peilmarge en aanvoeren kosten geen aanleg, dus ze staan niet in `cost`. Wat
    ze wel kosten is drooglegging, bedrijfsvoering en water, en dat staat hier als een
    BENOEMING in plaats van als een bedrag - een verzonnen bedrag zou hier erger zijn dan
    geen bedrag.

    Noem deze posten naast `cost`. Een maatregel die de kosten zichtbaar verlaagt en niets
    zichtbaars verhoogt, leest anders als gratis winst.
    """

    model_config = ConfigDict(frozen=True)

    topic: str = Field(..., description="De post: peilopzet, peilmarge of aanvoeren")
    magnitude: str = Field(
        ..., description="Hoe groot die post in dit antwoord is, met eenheid"
    )
    what_it_costs: str = Field(
        ...,
        description=(
            "Waar de prijs uit bestaat, in plaats van een bedrag. Noem dit in je "
            "terugkoppeling naast `cost`; anders leest de maatregel als gratis"
        ),
    )


class SolveResult(BaseModel):
    """Wat er nodig is, wat het oplevert, en of het kan."""

    model_config = ConfigDict(frozen=True)

    status: SolveStatus = Field(
        ...,
        description=(
            "exact = doel haalbaar en maatvoering bepaald; no_measure_needed = de "
            "waterstand blijft er al onder; action_infeasible = het doel ligt onder wat "
            "deze maatregel kan bereiken, maar een andere of een combinatie kan het "
            "misschien wel"
        ),
    )
    limit_reason: LimitReason = Field(
        LimitReason.NONE,
        description=(
            "Bij action_infeasible: measure_optimum als de maatregel zijn eigen optimum "
            "bereikt, physical_upper_bound als de maatvoering tegen een fysieke grens "
            "aanloopt"
        ),
    )

    magnitude: float = Field(..., description="Benodigde maatvoering, in `unit`")
    share_delta_pp: float | None = Field(
        None,
        description=(
            "De verschuiving in procentpunten, of `None` als deze grootheid geen aandeel "
            "is; komt uit `Action.area_share_delta`"
        ),
    )
    share_of_nl: str | None = Field(
        None,
        description="Waarvan `share_delta_pp` een percentage is; komt uit `Action.share_of_nl`",
    )
    magnitude_before: float = Field(
        0.0,
        description=(
            "De waarde van dezelfde grootheid VOOR de maatregel, in `unit`; komt uit "
            "`Action.current_magnitude`. Samen met `magnitude` is dit wat `MeasureChange` "
            "naar buiten brengt"
        ),
    )
    unit: str
    measure_nl: str
    cost: float | None = Field(
        None, description="Investeringskosten [EUR], werkwaarde; geen exploitatie"
    )
    cost_range: tuple[float, float] | None = Field(
        None,
        description=(
            "Onder- en bovengrens van de investeringskosten [EUR]. De bandbreedte staat "
            "erbij omdat een enkel getal valse precisie zou zijn"
        ),
    )

    state_before: PolderState
    state_after: PolderState

    target_dh_m: float | None = Field(
        None, description="Doelwaterstand; None bij een voorwaartse berekening"
    )
    dh_reference_m: float = Field(
        ..., description="Waterstandstijging zonder maatregel"
    )
    dh_with_measure_m: float = Field(
        ..., description="Waterstandstijging met maatregel"
    )

    feasible_dh_min_m: float = Field(
        ..., description="Laagste haalbare waterstandstijging met deze maatregel"
    )
    feasible_dh_max_m: float = Field(
        ..., description="Hoogste, oftewel de referentie zonder maatregel"
    )
    magnitude_at_optimum: float = Field(
        ..., description="Maatvoering waarbij feasible_dh_min_m wordt gehaald"
    )
    magnitude_optimum_kind: OptimumKind = Field(
        ...,
        description=(
            "Wat er gebeurt voorbij magnitude_at_optimum: interior = het wordt weer "
            "slechter, plateau = er verandert niets meer, saturated = er verandert niets "
            "meer omdat een andere grootheid de klem is, upper_bound = verder kan niet"
        ),
    )

    @property
    def dh_reduction_m(self) -> float:
        """De verlaging ten opzichte van de situatie zonder maatregel."""
        return self.dh_reference_m - self.dh_with_measure_m


class MeasureChange(EngineerOutputModel):
    """Wat deze maatregel met het watersysteem doet: voor, na, en het verschil.

    Vervangt `state_before` en `state_after`. Die gaven de HELE toestand twee keer terug,
    terwijl er per maatregel maar één grootheid verandert - de rest was in beide identiek en
    dus ruis. Wat er juist NIET in stond was het verschil in procentpunten en het relatieve
    verschil; die stonden nergens, terwijl de nieuwe waarde er drie keer stond.

    Dezelfde vorm voor alle maatregeltools: bergen verandert open water, afvoeren
    gemaalcapaciteit, vasthouden het retentie-areaal en aanvoeren de inlaat - maar de VRAAG
    is steeds dezelfde. Wie één tool kent, kent ze daarmee alle acht.

    **Lees dit blok altijd samen met `status`.** Bij `exact` is `after` een doel om te
    realiseren; bij `action_infeasible` is het de grens waarop de maatregel vastloopt en
    juist GEEN advies; bij `no_measure_needed` is het gelijk aan `before`.
    """

    name_nl: str = Field(
        ...,
        description=(
            "De maatregel die is doorgerekend: bergen, afvoeren, vasthouden of aanvoeren. "
            "Gebruik deze naam in de terugkoppeling; hij komt overeen met de naam in "
            "`description`"
        ),
    )
    unit: str = Field(
        ...,
        description=(
            "Eenheid van `before`, `after` en `delta`, met de grootheid erin - "
            "'ha open water', 'm3/s', 'ha land'. Samen met de getallen is dit wat je in een "
            "zin zet"
        ),
    )

    before: float = Field(
        ...,
        description=(
            "De waarde zoals het gebied er nu voor staat, in `unit`. Vaak NUL, en dat is "
            "geen ontbrekende invoer: een polder heeft standaard geen retentie en geen "
            "inlaat, dus nul is daar de juiste startwaarde"
        ),
    )
    after: float = Field(
        ...,
        description=(
            "De waarde na de maatregel, in `unit`. **Wat dit betekent hangt af van "
            "`status`, en dat verschil hoort gecontroleerd te worden voordat je het "
            "doorgeeft.** Bij `exact`: het getal dat gerealiseerd moet worden. Bij "
            "`action_infeasible`: de grens waarop deze maatregel vastloopt - dus GEEN "
            "advies, en meestal een extreme waarde zoals 100 % open water. Bij "
            "`no_measure_needed`: gelijk aan `before`, want er hoeft niets te gebeuren"
        ),
    )
    delta: float = Field(
        ...,
        description=(
            "De toename, in `unit`: `after` min `before`. Dit is wat er BIJ moet, en het "
            "hoort meestal in de eerste zin van een antwoord. Nul bij "
            "`status = no_measure_needed`"
        ),
    )
    delta_relative: float | None = Field(
        None,
        description=(
            "De toename ten opzichte van wat er al was, als fractie: 0,31 betekent 31 % "
            "meer. Zegt iets anders dan `delta` - 44 ha erbij is weinig op een grote polder "
            "en veel op een kleine. **`None` wanneer `before` nul is**, en dat is bij "
            "vasthouden en aanvoeren de normale situatie: 'oneindig veel meer dan niets' is "
            "geen bruikbare uitspraak. Gebruik dan `delta` en `after`"
        ),
    )
    delta_percentage_points: float | None = Field(
        None,
        description=(
            "De toename in PROCENTPUNTEN, alleen als de grootheid een aandeel is. `None` "
            "bij gemaal- en inlaatcapaciteit, want die zijn geen aandeel maar een "
            "capaciteit. **Noem er altijd `share_of_nl` bij**: de noemer verschilt per "
            "maatregel, en '59 procentpunt' zonder te zeggen waarvan is dubbelzinnig. Let "
            "ook op het verschil met `delta_relative`: bij bergen is 1,1 procentpunt "
            "hetzelfde als 31 % relatief, en die twee door elkaar halen is de klassieke "
            "fout in een terugkoppeling"
        ),
    )
    share_of_nl: str | None = Field(
        None,
        description=(
            "Waarvan `delta_percentage_points` een percentage is: 'het gebied' bij bergen, "
            "'het landoppervlak' bij vasthouden. Die noemers zijn verschillend omdat de "
            "maatregelen verschillend zijn - op open water kun je niets vasthouden - en "
            "daarom staat de noemer erbij in plaats van dat hij verondersteld wordt. `None` "
            "wanneer er geen aandeel is"
        ),
    )

    @classmethod
    def from_solve_result(cls, result) -> "MeasureChange":
        """Bouw het blok uit een `SolveResult`.

        `before` komt van de maatregel zelf (`Action.current_magnitude`), niet uit een diff
        van twee toestanden: alleen de maatregel weet welke grootheid hij verandert en in
        welke eenheid hij hem uitdrukt.
        """
        before = result.magnitude_before
        after = before + result.magnitude
        return cls(
            name_nl=result.measure_nl,
            unit=result.unit,
            before=before,
            after=after,
            delta=result.magnitude,
            delta_relative=(result.magnitude / before) if before else None,
            delta_percentage_points=result.share_delta_pp,
            share_of_nl=result.share_of_nl,
        )


class MeasureOutput(EngineerOutputModel):
    """Gedeelde uitvoer van de zes vuistregeltools.

    `measure` is het antwoord op "wat als ik dit doe": van welke waarde naar welke waarde,
    en hoeveel dat is. Het haalbare bereik en de status staan erbij omdat een doel buiten
    dat bereik geen getal verdient maar een uitleg.
    """

    data: Dict[str, Any] = Field(..., description="Ruwe uitkomsten en tussenresultaten")
    description: str = Field(
        ...,
        description=(
            "Twee uitlegbare zinnen, plus een derde met de aangenomen standaardwaarden "
            "als de beller er een heeft weggelaten"
        ),
    )

    status: SolveStatus = Field(
        ...,
        description=(
            "exact = doel haalbaar; no_measure_needed = niet nodig; action_infeasible = "
            "niet haalbaar met DEZE maatregel - een andere of een combinatie kan het "
            "misschien wel, dus dit is geen uitspraak over het probleem"
        ),
    )
    limit_reason: LimitReason = Field(
        LimitReason.NONE,
        description="Waarom het doel niet haalbaar was, indien van toepassing",
    )
    magnitude_optimum_kind: OptimumKind = Field(
        ...,
        description=(
            "Hoort bij magnitude_at_optimum_* in `data` en zegt wat er gebeurt als de "
            "maatregel groter wordt gemaakt dan die maatvoering: interior = de "
            "waterstandstijging wordt weer groter (vasthouden), plateau = er verandert "
            "niets meer (afvoeren), upper_bound = groter kan fysiek niet (bergen). Dit "
            "gaat dus over de maatvoering en niet over de waterstand: welke stijging "
            "haalbaar is staat in feasible_dh_min_m en feasible_dh_max_m"
        ),
    )
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description=(
            "Standaardwaarden waarmee gerekend is omdat ze niet zijn opgegeven. Leeg als "
            "de beller alles heeft ingevuld; anders is dit precies wat er nog aan het "
            "antwoord kan schuiven"
        ),
    )
    sensitivity: list[Sensitivity] = Field(
        default_factory=list,
        description=(
            "Per aangenomen veld het antwoord aan de uiteinden van zijn plausibele bereik. "
            "Dit is de spreiding van DIT antwoord en geen algemene uitspraak: het model is "
            "sterk over haalbaarheid en rangorde en zwak over maatvoering, en hier staat "
            "hoeveel. Geef het bereik door aan de gebruiker en niet alleen het getal"
        ),
    )
    caveats: list[ModelCaveat] = Field(
        default_factory=list,
        description=(
            "Structurele beperkingen die op dit antwoord van toepassing zijn: termen die "
            "niet in het model zitten of vragen die openstaan, met de richting waarin ze "
            "het antwoord kunnen schuiven. Bewust geen foutmarge - parametrische "
            "onzekerheid staat berekend in `sensitivity`, en een percentage op structurele "
            "modelfout zou verzonnen zijn"
        ),
    )

    measure: MeasureChange = Field(
        ...,
        description=(
            "Wat de maatregel met het systeem doet: van welke waarde naar welke waarde, en "
            "hoeveel dat is - absoluut, relatief en in procentpunten. Lees samen met "
            "`status`: bij een onhaalbaar doel is `after` de grens en geen advies"
        ),
    )

    dh_reference_m: float = Field(
        ..., description="Maximale waterstandstijging zonder maatregel [m]"
    )
    dh_with_measure_m: float = Field(
        ..., description="Maximale waterstandstijging met maatregel [m]"
    )
    feasible_dh_min_m: float = Field(
        ...,
        description=(
            "Laagst haalbare waterstandstijging met deze maatregel [m]; een doel "
            "hieronder is action_infeasible"
        ),
    )

    cost: float | None = Field(
        None,
        description=(
            "Investeringskosten [EUR], werkwaarde; geen exploitatie. **Null bij "
            "action_infeasible**: daar is `measure.after` de grens waarop de maatregel "
            "vastloopt en geen advies, dus een prijs eraan hangen zou een voorstel "
            "prijzen dat niet gedaan wordt. Wat die grens zou kosten staat dan in "
            "`cost_at_limit`. Null ook wanneer de maatregel geen prijs heeft; kijk dan in "
            "`priceless`"
        ),
    )
    cost_range: tuple[float, float] | None = Field(
        None, description="Onder- en bovengrens van de investeringskosten [EUR]"
    )
    cost_at_limit: float | None = Field(
        None,
        description=(
            "Wat de maatvoering in `measure.after` zou kosten, alleen gevuld bij "
            "action_infeasible [EUR]. **Geen offerte en geen advies**: `measure.after` is "
            "daar de grens waarop de maatregel vastloopt, dus bij 100 % open water staat "
            "hier 521 miljoen euro. Noem dit bedrag niet zonder de status erbij"
        ),
    )
    cost_range_at_limit: tuple[float, float] | None = Field(
        None, description="Onder- en bovengrens bij `cost_at_limit` [EUR]"
    )
    priceless: list[PricelessPost] = Field(
        default_factory=list,
        description=(
            "Posten in dit antwoord die geen bedrag hebben maar wel een prijs: peilopzet, "
            "peilmarge en aanvoeren. Leeg als er geen zijn. **Noem ze naast `cost`.** Ze "
            "VERLAGEN `cost` zichtbaar - een peilmarge van 30 cm brengt de benodigde "
            "berging van 68 naar 38 ha en de kosten van 9,2 naar 5,1 miljoen euro - en wat "
            "ze in plaats daarvan kosten staat in geen enkel getal. Noem je ze niet, dan "
            "presenteer je zo'n maatregel als gratis winst"
        ),
    )

    @model_serializer(mode="wrap")
    def _round_output(self, handler):
        """Rond de hele uitvoer af op significante cijfers; zie SIGNIFICANT_DIGITS."""
        return round_floats(handler(self))

    @classmethod
    def from_solve_result(
        cls,
        result,
        data,
        description,
        assumptions=(),
        sensitivity=(),
        caveats=(),
        priceless=(),
        **extra,
    ):
        # Bij een onhaalbaar doel verhuist de prijs naar `cost_at_limit`. De handleiding
        # waarschuwde er wel voor - lees `measure.after` nooit zonder `status` - en dat
        # werkt zolang de beller de handleiding leest. Het veld leeghalen is robuuster dan
        # daarop vertrouwen: er stond 521 miljoen euro naast "100 % open water", en dat
        # leest als een offerte.
        at_limit = result.status is SolveStatus.ACTION_INFEASIBLE
        return cls(
            data=data,
            description=description,
            sensitivity=list(sensitivity),
            caveats=list(caveats),
            status=result.status,
            limit_reason=result.limit_reason,
            magnitude_optimum_kind=result.magnitude_optimum_kind,
            assumptions=list(assumptions),
            priceless=[PricelessPost(**post) for post in priceless],
            measure=MeasureChange.from_solve_result(result),
            dh_reference_m=result.dh_reference_m,
            dh_with_measure_m=result.dh_with_measure_m,
            feasible_dh_min_m=result.feasible_dh_min_m,
            cost=None if at_limit else result.cost,
            cost_range=None if at_limit else result.cost_range,
            cost_at_limit=result.cost if at_limit else None,
            cost_range_at_limit=result.cost_range if at_limit else None,
            **extra,
        )
