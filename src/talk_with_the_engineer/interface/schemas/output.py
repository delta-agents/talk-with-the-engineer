"""De uitvoermodellen van de tools: het antwoord plus wat je ervan mag geloven.

Dit is de INTERFACE-kant van een uitkomst. `core/results.py` draagt wat de kern uitrekent -
`SolveResult` en de statusenums - en hier komt daar bij wat een aanroeper nodig heeft om
het antwoord te kunnen navertellen: de aannames, de spreiding, de caveats en de posten
zonder bedrag.

Die scheiding is niet cosmetisch. Stond dit in de kern, dan importeerde de kern zijn eigen
epistemieklaag, en dat is de pijl terug die `tests/test_core_boundary.py` verbiedt - hij
sloot letterlijk een cirkel: results -> epistemics -> inverse -> results.
"""

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, model_serializer

from talk_with_the_engineer.core.results import (
    LimitReason,
    OptimumKind,
    SolveStatus,
    round_floats,
)
from talk_with_the_engineer.epistemics.assumptions import Assumption
from talk_with_the_engineer.epistemics.caveats import ModelCaveat
from talk_with_the_engineer.epistemics.uncertainty import Sensitivity
from talk_with_the_engineer.interface.schemas.base import EngineerOutputModel


# Waarom dit blok bestaat. "Geen prijs" is niet "gratis", en het verschil bepaalt de
# UITKOMST en niet alleen de rapportage: een prijsloze maatregel die als nul meetelt, koopt
# in de pakketzoeker inundatiemarge zonder tegenprijs, en dan verschuift het goedkoopste
# pakket zonder dat er iets aan de hydrologie is veranderd. Zie `TargetLevelAction`.
#
# Aan de toolkant weegt hetzelfde even zwaar. Een peilmarge van 30 cm brengt de benodigde
# berging van 68 naar 38 ha en de kosten van 9,2 naar 5,1 miljoen euro; zonder deze post
# staat er in het antwoord niets dat eraan herinnert dat die 30 cm iets kost.
#
# Dit staat als comment en niet in de docstring hieronder: die komt in het UITVOERSCHEMA
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


class MeasureChange(EngineerOutputModel):
    """Wat deze maatregel met het watersysteem doet: voor, na, en het verschil.

    Drie getallen over ÉÉN grootheid, en niet de hele toestand voor en na. Een maatregel
    verandert precies één veld, dus twee volledige toestanden zijn op één getal na identiek
    en de rest is ruis. Wat een lezer nodig heeft is smaller en scherper: de beginwaarde, de
    eindwaarde, en het verschil - ook in procentpunten waar de grootheid een aandeel is.

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
            "daar de grens waarop de maatregel vastloopt - soms letterlijk 100 % open "
            "water - en de prijs van zo'n grens is een absurd bedrag, geen voorstel. Noem "
            "dit bedrag niet zonder de status erbij"
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
            "VERLAGEN `cost` zichtbaar - een peilmarge kan de benodigde maatregel bijna "
            "halveren - en wat ze in plaats daarvan kosten staat in geen enkel getal. Noem "
            "je ze niet, dan presenteer je zo'n maatregel als gratis winst"
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
