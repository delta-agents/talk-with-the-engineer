"""In- en uitvoer van de pakketzoeker: het goedkoopste pakket dat de eisen samen haalt.

De tien maatregeltools rekenen een gegeven maatregel door. Deze vraag is een andere: welke
COMBINATIE van maatregelen haalt de eisen, en wat kost die. Zodra er meerdere maatregelen en
meerdere eisen zijn, is het antwoord geen inverse meer maar een optimalisatie - en dan is de
maatvoering zelf de minst robuuste uitspraak die eruit komt. Daarom staat er naast het
goedkoopste pakket wat er niet van te onderscheiden is (`near_optimal`), waar de maatvoering
vrij is (`ranges`), en welke maatregelen geen prijs hebben (`priceless`).
"""

from typing import Any, Dict, Literal

from pydantic import ConfigDict, Field, PrivateAttr, model_serializer, model_validator
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerOutputModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    Assumption,
    ModelCaveat,
    RainfallInput,
    WaterSystemInput,
    hide_null_branch_and_bound,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.drought import (
    DroughtStatisticInput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureRole,
    PricelessPost,
    SolveStatus,
    round_floats,
)

REQUIREMENT_FIELDS = ("max_dh_total_m", "min_storage_mm", "max_shortfall_mm")
"""De drie eisen. Minstens een is verplicht; zonder eis is niets doen het goedkoopst."""

DROUGHT_WINDOW_DAYS = 30
"""Het venster waarover een zelf opgegeven tekort wordt uitgesmeerd, in dagen."""

GROWING_SEASON_DAYS = 183
"""Het venster waarover de droogtestatistiek zijn cumulatieve tekort optelt, in dagen."""


class OptimizeInput(RainfallInput, DroughtStatisticInput, WaterSystemInput):
    """Het gebied, de belasting, en de eisen waaraan het pakket tegelijk moet voldoen."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "max_dh_total_m": 1.0,
                "min_storage_mm": 20,
            }
        }
    )

    # BESTAAND EN EXTRA ZIJN TWEE VELDEN, ook hier. `target_level_rise_m` is de opzet die er
    # AL staat en de maatregel is wat de zoeker daarbovenop legt - hetzelfde onderscheid als
    # `discharge_capacity_m3_per_sec` naast de maatregel afvoeren. Dat is geen dubbeltelling
    # maar een begintoestand: de inundatienorm wordt boven het OORSPRONKELIJKE peil gemeten,
    # dus wie zijn bestaande opzet weglaat krijgt te veel marge toebedeeld en een pakket dat
    # de norm overschrijdt zodra hij het bovenop de bestaande stand uitvoert.
    target_level_rise_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilopzet die er AL staat: hoeveel het streefpeil nu hoger ligt dan het "
            "oorspronkelijke peil [m]. Nul is een polder op zijn oorspronkelijke peil. Dit "
            "is de bestaande stand en niet de maatregel - de zoeker bepaalt zelf hoeveel "
            "opzet hij er bovenop legt, en meldt dat als de maatregel 'peilopzet'. Laat je "
            "dit weg bij een polder die al is opgezet, dan rekent de tool met te veel marge "
            "tot inundatie en te weinig zomervoorraad"
        ),
    )
    level_margin_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilmarge: hoe diep onder het streefpeil het gemaal mag doormalen [m], de "
            "afspraak die voorbemaling mogelijk maakt. Nul is het klassieke gedrag, waarbij "
            "het gemaal op streefpeil stopt"
        ),
    )
    days_to_retain_discharge: int | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(0),
        description=(
            "Aantal extra dagen dat het water op het land wordt vastgehouden zodra de "
            "zoeker vasthouden inzet. Kan niet negatief zijn; nul betekent geen vertraging. "
            "Weet je dit niet, laat het veld dan weg in plaats van het te schatten; de tool "
            "rekent met een vaste waarde en meldt dat in `assumptions`"
        ),
    )

    # --- de eisen -------------------------------------------------------------------
    max_dh_total_m: float | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(0.0),
        description=(
            "Inundatienorm: hoe hoog de waterstand ten hoogste mag komen boven het "
            "OORSPRONKELIJKE peil [m], dus inclusief de peilopzet die de zoeker zelf "
            "inzet. Een gangbare norm voor bebouwing ligt rond 0,5 tot 1,0 m"
        ),
    )
    min_storage_mm: float | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(0.0),
        description=(
            "Minimale voorraad onder het streefpeil [mm over de polder]. Dit is een "
            "PEIL-uitspraak: een statische eigenschap van de peilband, die geen inlaat "
            "meerekent en niets over de tijd zegt. Wil je de droge kant over de tijd, "
            "gebruik dan `max_shortfall_mm`"
        ),
    )
    max_shortfall_mm: float | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(0.0),
        description=(
            "Maximaal onvervuld tekort na de droogteperiode [mm over de polder]. Dit is een "
            "WATERSTAND-uitspraak uit een doorrekening, en de enige eis waarin een inlaat "
            "meetelt - dus de eis die aanvoeren in het pakket kan brengen. Vereist een "
            "droogte: `deficit_mm_per_day`, of het tripel `drought_region` + "
            "`drought_scenario` + `drought_return_period`. De bui blijft ook hier verplicht, "
            "want de zoeker mag peilopzet inzetten en die betaalt in marge tot inundatie"
        ),
    )

    # --- de droogte, alleen nodig bij een eis op de waterstand-as --------------------
    deficit_mm_per_day: float | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(0.0),
        description=(
            "Netto neerslagtekort [mm/dag]: verdamping minus neerslag. Een warme zomerdag "
            "zonder regen zit rond 4 mm/dag; ordegrootte 2 tot 5 mm/dag. Geef dit OF kies "
            "een droogte met `drought_region`, `drought_scenario` en "
            "`drought_return_period`; allebei tegelijk wordt geweigerd. Alleen nodig bij "
            "`max_shortfall_mm`"
        ),
    )
    length_days: int | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(1),
        description=(
            "Hoeveel dagen het tekort aanhoudt. Weet je dit niet, laat het veld dan weg; de "
            "tool rekent met een vast venster en meldt dat in `assumptions`"
        ),
    )

    # --- de zoekruimte en de uitvoer -------------------------------------------------
    detail: bool = Field(
        False,
        description=(
            "Zet dit aan om ALLE onderzochte combinaties terug te krijgen in `packages`, "
            "ook de onhaalbare met de reden erbij. Standaard staat er alleen het antwoord: "
            "het goedkoopste pakket, wat er niet van te onderscheiden is, en de "
            "bandbreedtes"
        ),
    )

    _cumulative_deficit_mm: float | None = PrivateAttr(default=None)
    """Het opgezochte maximaal cumulatief neerslagtekort [mm], of `None`.

    Een privéveld en geen gewoon veld: het is een UITKOMST van het valideren en hoort in de
    uitvoer thuis, niet in het invoerschema waar het een beller zou verleiden het zelf te
    vullen. `None` zodra de beller het tekort zelf opgaf; dan is er niets opgezocht.
    """

    @property
    def cumulative_deficit_mm(self) -> float | None:
        """Het cumulatief neerslagtekort waaruit `deficit_mm_per_day` is afgeleid [mm]."""
        return self._cumulative_deficit_mm

    @model_validator(mode="after")
    def enforce_the_advertised_bounds(self):
        """Handhaaf de grenzen die het schema adverteert, met de reden erbij.

        Het schema draagt een `minimum` per veld, maar een client hoeft zich daar niet aan
        te houden - en een grens die wel geadverteerd en niet gehandhaafd wordt, laat een
        betekenisloze vraag door met een antwoord dat betekenisvol oogt: een negatieve
        voorraadeis is "al gehaald", een negatief tekort is een natte droogte zonder
        tekort. Elke zin hieronder zegt daarom wat de waarde betekent, niet alleen dat hij
        te laag is.
        """
        refusals = (
            (
                "max_dh_total_m",
                self.max_dh_total_m is not None and self.max_dh_total_m < 0,
                "een negatieve inundatienorm bestaat niet. Nul betekent 'geen stijging "
                "toegestaan'; geef nul of een positieve norm in meters",
            ),
            (
                "min_storage_mm",
                self.min_storage_mm is not None and self.min_storage_mm < 0,
                "een negatieve voorraadeis is altijd gehaald en dus geen eis. Geef nul of "
                "een positieve voorraad in mm over de polder",
            ),
            (
                "max_shortfall_mm",
                self.max_shortfall_mm is not None and self.max_shortfall_mm < 0,
                "een negatief tekort bestaat niet. Nul is streng maar geldig: geen "
                "onvervulde vraag na de droogteperiode",
            ),
            (
                "deficit_mm_per_day",
                self.deficit_mm_per_day is not None and self.deficit_mm_per_day <= 0,
                "een tekort van nul of minder is geen droogte maar een natte periode; "
                "daarvoor zijn de eisen op de natte kant. Geef een positief tekort in "
                "mm/dag, ordegrootte 2 tot 5",
            ),
            (
                "length_days",
                self.length_days is not None and self.length_days < 1,
                "een droogte van nul dagen is geen droogte; er valt dan niets door te "
                "rekenen. Geef minstens 1 dag, of laat het veld weg voor het "
                "standaardvenster",
            ),
            (
                "days_to_retain_discharge",
                self.days_to_retain_discharge is not None
                and self.days_to_retain_discharge < 0,
                "dit is het aantal EXTRA dagen dat de afvoer wordt vertraagd en kan niet "
                "negatief zijn; nul betekent geen vertraging",
            ),
        )
        broken = [
            f"`{name}`={getattr(self, name):g}: {reason}"
            for name, is_broken, reason in refusals
            if is_broken
        ]
        if broken:
            raise ModelRetry(" En ".join(broken) + ".")
        return self

    @model_validator(mode="after")
    def require_at_least_one_requirement(self):
        """Zonder eis is het goedkoopste pakket altijd niets doen."""
        if all(getattr(self, name) is None for name in REQUIREMENT_FIELDS):
            raise ModelRetry(
                "Geef minstens een eis op: `max_dh_total_m` [m] voor de inundatienorm, "
                "`min_storage_mm` [mm] voor de voorraad onder streefpeil, of "
                "`max_shortfall_mm` [mm] voor het onvervulde tekort na een droogteperiode. "
                "Zonder eis is het goedkoopste pakket altijd niets doen."
            )
        return self

    @model_validator(mode="after")
    def resolve_the_drought(self):
        """Vul het tekort en het venster in, of leg uit waarom de eis niet te meten is.

        Het venster hangt af van waar het tekort vandaan komt: bij een zelf opgegeven tekort
        een maand, en bij de statistiek het groeiseizoen, want dat is het venster waarover
        die statistiek zijn tekort optelt. Dertig dagen zou van 269 mm cumulatief 9 mm/dag
        maken, en dat is geen droogte maar een rekenfout.

        Idempotent, want een validator met `mode="after"` kan meer dan een keer over
        hetzelfde model lopen: het opzoeken gebeurt alleen zolang er nog geen tekort staat.
        """
        from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
            available_return_periods,
            cumulative_deficit_mm,
        )

        chosen = self.drought_statistic_choice
        if not chosen and self.deficit_mm_per_day is None:
            # Geen droogte in het spel: het venster doet niets en hoort dus ook niet als
            # aanname in de uitvoer te staan.
            return self._refuse_a_shortfall_without_a_drought()

        if self.length_days is None:
            self.length_days = GROWING_SEASON_DAYS if chosen else DROUGHT_WINDOW_DAYS
            self._assumed_fields.add("length_days")

        if chosen and self.deficit_mm_per_day is not None:
            if self._cumulative_deficit_mm is None:
                raise ModelRetry(
                    "Geef het tekort op EN uit de statistiek is dubbelop: "
                    f"`deficit_mm_per_day`={self.deficit_mm_per_day:g} staat naast een "
                    "gekozen droogte. Laat een van de twee weg, anders is niet te zien "
                    "welk van beide het antwoord stuurt."
                )
            return self

        if chosen:
            total_mm = cumulative_deficit_mm(
                self.drought_region, self.drought_scenario, self.drought_return_period
            )
            if total_mm is None:
                usable = [
                    period
                    for period in available_return_periods()
                    if cumulative_deficit_mm(
                        self.drought_region, self.drought_scenario, period
                    )
                    is not None
                ]
                raise ModelRetry(
                    f"Voor {self.drought_region!r} in scenario "
                    f"{self.drought_scenario!r} is er geen tekort bij een herhaaltijd van "
                    f"{self.drought_return_period} jaar: die valt buiten de reeks waarop "
                    "deze statistiek is gefit. Beschikbaar zijn hier "
                    f"{', '.join(str(period) for period in usable)}. Extrapoleren zou een "
                    "getal verzinnen waar het rapport er geen heeft."
                )
            self._cumulative_deficit_mm = total_mm
            self.deficit_mm_per_day = total_mm / self.length_days
        return self

    def _refuse_a_shortfall_without_a_drought(self):
        """De tekort-eis kan niet worden gemeten zonder droogte om hem op te meten."""
        if self.max_shortfall_mm is not None:
            raise ModelRetry(
                "`max_shortfall_mm` vraagt om een droogte; zonder droogte is er geen "
                "tekort om te meten. Geef `deficit_mm_per_day` [mm/dag] op, of kies een "
                "droogte met `drought_region`, `drought_scenario` en "
                "`drought_return_period` samen."
            )
        return self

    @property
    def requirements_set(self) -> tuple[str, ...]:
        """Welke van de drie eisen deze aanroep stelt."""
        return tuple(
            name for name in REQUIREMENT_FIELDS if getattr(self, name) is not None
        )


class MeasureQuantity(EngineerOutputModel):
    """Een maatregel met zijn maatvoering, in de eenheid waarin die maatregel meet."""

    name_nl: str = Field(
        ...,
        description="De maatregel: vasthouden, bergen, afvoeren, peilopzet of aanvoeren",
    )
    unit: str = Field(
        ..., description="Eenheid van `magnitude`, verschilt per maatregel"
    )
    magnitude: float = Field(..., description="Hoeveel er van deze maatregel in zit")


class RequirementMiss(EngineerOutputModel):
    """Hoeveel een eis wordt gemist - met per eis de echte grens uit een eigen doorrekening."""

    requirement: str = Field(
        ..., description="De gemiste eis: inundatie, voorraad of tekort"
    )
    required: float = Field(
        ..., description="Wat de eis vraagt, in de eenheid van die eis"
    )
    reached: float = Field(
        ...,
        description=(
            "Wat het beste onderzochte pakket op deze as haalde, zelfde eenheid. De "
            "gezamenlijke zoektocht optimaliseert kosten, dus dit is een waarneming en "
            "geen grens; de grens staat in `achievable_alone`"
        ),
    )
    achievable_alone: float = Field(
        ...,
        description=(
            "Het beste dat de vijf maatregelen SAMEN op deze ene as bereiken, los van de "
            "andere eisen [zelfde eenheid]. Uit een eigen doorrekening die de as zelf "
            "optimaliseert, dus verder dan dit komt het met deze maatregelen echt niet"
        ),
    )
    alone_feasible: bool = Field(
        ...,
        description=(
            "Of de eis op zichzelf haalbaar is. Is elke gemiste eis dat en is er toch "
            "geen pakket, dan conflicteren de eisen - een ander gesprek dan 'het kan "
            "niet': een van de eisen versoepelen kan dan genoeg zijn"
        ),
    )
    missed_by: float = Field(
        ...,
        description=(
            "Hoeveel er in de gezamenlijke zoektocht tekortkwam, zelfde eenheid: de "
            "kleinste geziene afstand, geen grens"
        ),
    )


class PackageReading(EngineerOutputModel):
    """Een pakket: welke maatregelen, hoe groot, wat het kost, en wat het haalt."""

    measures: list[MeasureQuantity] = Field(
        ..., description="De ingezette maatregelen; wat er niet in zit staat er niet in"
    )
    cost: float = Field(
        ...,
        description=(
            "Investeringskosten van de maatregelen die een prijs HEBBEN [EUR]. Dus niet de "
            "prijs van het pakket zodra `priceless` niet leeg is - wat er dan ontbreekt "
            "staat daar"
        ),
    )
    cost_range: tuple[float, float] | None = Field(
        None,
        description=(
            "Onder- en bovengrens van de investeringskosten [EUR], of null zodra er een "
            "prijsloze maatregel in zit: dan is er geen prijs en dus ook geen band om een "
            "prijs. De band komt per maatregel uit zijn eigen onderbouwing"
        ),
    )
    replacement_cost: float = Field(
        ...,
        description=(
            "Dezelfde maatvoering, geprijsd als VERVANGING in plaats van als toename [EUR]. "
            "Een tweede lezing en geen correctie: lineair rekenen onderschat een kleine "
            "uitbreiding, want je koopt een gemaal en geen m3/s. Deze lezing verandert de "
            "rangorde; zie `indistinguishable_as_replacement`"
        ),
    )
    binding: list[str] = Field(
        default_factory=list,
        description=(
            "Welke eisen op hun grens liggen. Dit is waar de prijs vandaan komt: laat je "
            "een bindende eis vallen, dan wordt het pakket goedkoper, en een niet-bindende "
            "eis kost niets"
        ),
    )
    priceless: list[str] = Field(
        default_factory=list,
        description=(
            "Ingezette maatregelen die geen bedrag hebben. Peilopzet kost drooglegging en "
            "aanvoeren kost water; dat zijn verdringingsvragen en geen euro's. Meld ze "
            "altijd mee - noem je ze niet, dan presenteer je ze als gratis winst"
        ),
    )
    dh_total_m: float = Field(
        ...,
        description="Waterstandstijging boven het OORSPRONKELIJKE peil [m], inclusief opzet",
    )
    storage_mm: float = Field(
        ..., description="Voorraad onder het streefpeil [mm over de polder]"
    )
    shortfall_mm: float | None = Field(
        None,
        description=(
            "Onvervuld tekort na de droogteperiode [mm], of null zonder droogte-invoer"
        ),
    )
    feasible: bool = Field(
        ..., description="Haalt dit pakket alle gestelde eisen tegelijk?"
    )


class MeasureRangeReading(EngineerOutputModel):
    """Wat een maatregel in het bijna-optimale gebied doet, en tussen welke grenzen.

    De twee grenzen komen uit twee verschillende dingen, en dat is het hele punt: de
    onderkant uit de EIS - minder haalt de norm niet - en de bovenkant uit de PRIJSBAND -
    meer koopt niets meer binnen wat we van de prijzen weten. Geen van beide komt uit de
    zoeker, dus dit interval is niet zoekerafhankelijk.
    """

    name_nl: str = Field(..., description="De maatregel")
    unit: str = Field(..., description="Eenheid van de twee grenzen")
    magnitude_min: float = Field(
        ...,
        description="Ondergrens: wat de eis vraagt; daaronder wordt de eis niet gehaald",
    )
    magnitude_max: float = Field(
        ...,
        description=(
            "Bovengrens van het interval; waar hij vandaan komt staat in "
            "`magnitude_max_source`, en dat verschil bepaalt hoe je hem leest"
        ),
    )
    magnitude_max_source: Literal["prijsband", "eis", "zoekgrens"] | None = Field(
        None,
        description=(
            "Waar de bovengrens vandaan komt. `prijsband`: meer koopt niets binnen wat we "
            "van de prijzen weten. `eis`: meer maakt een gestelde eis onhaalbaar. "
            "`zoekgrens`: niets stopte hem behalve het einde van de zoekruimte - lees dat "
            "NIET als koopadvies, elke maat vanaf de ondergrens voldoet. Null wanneer de "
            "maatregel niet meedoet"
        ),
    )
    role: MeasureRole = Field(
        ...,
        description=(
            "`forced` zit in ELK pakket dat binnen de marge even goed is - hier is geen "
            "keuze. `optional` zit in sommige en niet in andere - daar is wel een keuze, en "
            "die is niet van ons. `absent` zit in geen enkel pakket in het gebied; waarom "
            "staat in `absent_reason`"
        ),
    )
    absent_reason: Literal["draagt_niet_bij", "buiten_prijsband"] | None = Field(
        None,
        description=(
            "Alleen bij rol `absent`, en gemeten aan het beste pakket: `draagt_niet_bij` "
            "betekent dat meer van deze maatregel geen enkele gestelde eis verbetert; "
            "`buiten_prijsband` betekent dat hij wel bijdraagt maar elke inzet buiten de "
            "prijsband van het beste pakket valt. Voor een bestuurder is dat het verschil "
            "tussen een maatregel die nooit meedeed en een die afviel op prijs"
        ),
    )


class OptimizeOutput(EngineerOutputModel):
    """Het gebied in plaats van het punt: het goedkoopste pakket, plus wat het niet uitsluit.

    Lees `best` nooit alleen. Een optimum is alleen optimaal voor wat er gemodelleerd is, en
    wat een waterschap daarnaast heeft - draagvlak, uitvoerbaarheid, een prijs die eigenlijk
    een trap is - leeft naast dat punt. `ranges` zegt hoeveel ruimte er is, `near_optimal`
    welke pakketten even goed zijn, en `priceless` wat er geen bedrag heeft.
    """

    data: Dict[str, Any] = Field(..., description="Ruwe uitkomsten en tussenresultaten")
    description: str = Field(
        ...,
        description=(
            "De uitlegbare zinnen bij dit antwoord: wat vastzit, wat vrij is, wat de twee "
            "kostenlezingen zeggen, en welke standaardwaarden zijn aangenomen"
        ),
    )
    status: SolveStatus = Field(
        ...,
        description=(
            "`exact` als er een pakket is, `no_measure_needed` als het gebied de eisen al "
            "haalt zonder maatregel, en `problem_infeasible` als GEEN enkele combinatie ze "
            "haalt. Lees `best` niet zonder dit veld: bij `problem_infeasible` is er geen "
            "pakket en staat de kleinste overschrijding in `missed`"
        ),
    )

    best: PackageReading | None = Field(
        None,
        description=(
            "Het goedkoopste pakket dat alle eisen haalt, of null zodra er geen is. Geef "
            "dit niet door als HET antwoord zonder `ranges` en `near_optimal` ernaast"
        ),
    )
    near_optimal: list[PackageReading] = Field(
        default_factory=list,
        description=(
            "De ANDERE pakketten die binnen de prijsband even goed zijn als `best`, "
            "goedkoopste eerst. Leeg betekent: er is binnen de prijsband geen alternatief. "
            "Ontdubbeld op maatvoering, want een grotere combinatie waarin de extra "
            "maatregelen naar nul gaan valt samen met een kleinere en is dus hetzelfde "
            "antwoord"
        ),
    )
    priced_cost_range: tuple[float, float] | None = Field(
        None,
        description=(
            "Onder- en bovengrens van de investering over het GEPRIJSDE deel van het "
            "beste pakket [EUR] - het interval waar `cost_epsilon` uit is afgeleid, zodat "
            "dat getal narekenbaar is. Null zodra er niets geprijsd in het pakket zit"
        ),
    )
    cost_epsilon: float = Field(
        ...,
        description=(
            "Hoe ver twee prijzen relatief uit elkaar mogen liggen om nog hetzelfde te zijn. "
            "Dit getal is niet afgesproken maar AFGELEID: het is de relatieve breedte van de "
            "prijsband over het GEPRIJSDE deel van het goedkoopste pakket, en dus per "
            "maatregelmix anders. Nul zodra er in het hele pakket niets zit dat een prijs "
            "heeft; met een prijsloze maatregel ernaast blijft hij dus gewoon gevuld"
        ),
    )
    ranges: list[MeasureRangeReading] = Field(
        default_factory=list,
        description=(
            "Per maatregel de rol en de vrije maatvoering; leeg zodra er geen maatregel "
            "nodig is, want dan is er geen gebied om rollen in te geven. Het interval is "
            "coordinaatgewijs - een maatregel beweegt en de andere staan vast - en dus een "
            "ONDERGRENS op de werkelijke speelruimte"
        ),
    )
    indistinguishable_as_replacement: list[PackageReading] = Field(
        default_factory=list,
        description=(
            "De ANDERE pakketten die in de vervangingslezing niet van `best` te onderscheiden "
            "zijn, want hun prijsbanden overlappen. Staat hier iets in, dan kan dit model "
            "niet zeggen welk van die pakketten het goedkoopst is - en dat is het eerlijke "
            "antwoord, geen ontbrekend antwoord. Leeg betekent: de rangorde houdt ook in die "
            "tweede lezing"
        ),
    )
    missed: list[RequirementMiss] = Field(
        default_factory=list,
        description=(
            "Alleen als er geen pakket is: per eis de kleinste overschrijding over alle "
            "onderzochte combinaties. Zo is 'het kan niet' net zo navolgbaar als 'het kan'. "
            "Per eis afzonderlijk, dus twee overschrijdingen kunnen van twee verschillende "
            "combinaties komen - tel ze niet bij elkaar op tot de afstand van een pakket"
        ),
    )
    packages: list[PackageReading] = Field(
        default_factory=list,
        description=(
            "Alle onderzochte combinaties, ook de onhaalbare; alleen gevuld met `detail`"
        ),
    )

    assumptions: list[Assumption] = Field(
        default_factory=list,
        description="Standaardwaarden waarmee gerekend is omdat ze niet zijn opgegeven",
    )
    caveats: list[ModelCaveat] = Field(
        default_factory=list,
        description="Structurele beperkingen die op dit antwoord van toepassing zijn",
    )
    priceless: list[PricelessPost] = Field(
        default_factory=list,
        description=(
            "Posten in dit antwoord die geen bedrag hebben maar wel een prijs, met wat ze "
            "in plaats daarvan kosten"
        ),
    )

    @model_serializer(mode="wrap")
    def _round_output(self, handler):
        """Rond de hele uitvoer af op significante cijfers; zie SIGNIFICANT_DIGITS."""
        return round_floats(handler(self))
