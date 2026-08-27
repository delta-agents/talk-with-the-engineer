"""Maatregel aanvoeren: meer inlaatcapaciteit tegen een neerslagtekort.

Dezelfde transitie als afvoeren en dezelfde rekenkern, met de klem gespiegeld. Wat wél
eigen is, is alles eromheen - en dat is precies de reden dat dit een eigen bestand met
eigen modellen heeft in plaats van een vlag op de afvoertool:

| | afvoeren | aanvoeren |
|---|---|---|
| aandrijving | een bui van 48 tot 192 uur | een tekort van weken |
| exogene invoer | STOWA-neerslagstatistiek | tekort in mm/dag maal een aantal dagen |
| doel | de stijging onder een grens houden | de waterstand boven een ondergrens houden |
| kunstwerk | gemaal, 1 tot 5 l/s/ha | inlaat, 0,3 tot 0,4 l/s/ha |
| prijs | investering per m3/s | geen; wat aanvoer kost is het water |

Zie PLAN_UITWISSELING_EN_NETWERK.md Sec. 2: verenig de transitie, verenig de toestand,
verenig de tool niet.
"""

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerOutputModel
from pydantic import PrivateAttr

from talk_with_the_engineer.models.modelset_rules_of_thumb.drought import (  # noqa: F401
    DROUGHT_REGIONS,
    DROUGHT_RETURN_PERIODS,
    DROUGHT_SCENARIOS,
    SOURCE_RIVERS,
    SourceVolumeInput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    Assumption,
    ModelCaveat,
    Sensitivity,
    WaterSystemInput,
    discharge_capacity_in_all_units,
    discharge_capacity_to_m3_per_sec,
    hide_null_branch,
    one_unit_only,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureChange,
    PricelessPost,
    SolveStatus,
    round_floats,
)

from pydantic import model_serializer


# De droogte-as woont in `drought.py`, samen met de mixins die hem lezen. Hier staat een
# her-export en geen tweede lijst: `DROUGHT_REGIONS` en de andere twee zijn de keuzelijsten
# van dit invoerschema en worden onder deze naam geimporteerd, ook door de tests.
GROWING_SEASON_DAYS = 183
"""Het venster waarover het cumulatief neerslagtekort is bepaald: 1 april tot 1 oktober.

Dit is het seizoen uit `drought_statistics.json` zelf, en dus het enige venster waarvan we
weten dat het bij de statistiek hoort. Het is een BOVENgrens op het echte accumulatievenster:
het maximum wordt in de meeste jaren voor 1 oktober bereikt, dus het tekort per dag komt hier
aan de milde kant uit. Een piekdatum verzinnen zou dat scherper maken en niet beter - wie het
korter wil, zet `length_days` zelf.
"""


class DeficitInput(SourceVolumeInput):
    """Het neerslagtekort: het exogene deel van de droogte-invoer.

    Twee wegen naar dezelfde twee getallen. Je geeft het tekort zelf op met
    `deficit_mm_per_day`, of je kiest een droogte uit de statistiek met
    `drought_region` + `drought_scenario` + `drought_return_period` en laat de tool het
    tekort eruit halen. Dat tripel is de tegenhanger van `return_period` op de natte kant:
    dezelfde herkomst (KNMI'23 / STOWA), dezelfde herhaaltijd-logica.

    Beide tegelijk is een invoerfout en wordt geweigerd, want dan is niet te zien welk van
    de twee het antwoord heeft gestuurd.

    Het tripel en de bron erven uit `SourceVolumeInput`: hetzelfde tripel dat hier de vraag
    kiest, kiest daar het aanbod. Dat is de hele reden dat die twee bij elkaar staan - een
    zeldzamere droogte hoort de vraag te verhogen en het aanbod te verlagen, en niet alleen
    het eerste.
    """

    deficit_mm_per_day: float | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Netto neerslagtekort [mm/dag]: verdamping minus neerslag. Een warme zomerdag "
            "zonder regen zit rond 4 mm/dag; ordegrootte 2 tot 5 mm/dag. Dit is "
            "gebiedsspecifiek en seizoensgebonden, dus er is bewust geen standaardwaarde: "
            "geef hem op, OF kies een droogte met `drought_region`, `drought_scenario` en "
            "`drought_return_period` en laat de tool hem uit de statistiek halen. Een van "
            "de twee is verplicht en allebei tegelijk wordt geweigerd."
        ),
    )
    length_days: int | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Hoeveel dagen het tekort aanhoudt. Weet je dit niet, laat het veld dan weg in "
            "plaats van het te schatten; de tool rekent met 30 dagen en meldt dat in "
            "`assumptions`. Kies je een droogte uit de statistiek, dan is de "
            "standaardwaarde het groeiseizoen van 183 dagen, want dat is het venster "
            "waarover die statistiek zijn tekort optelt."
        ),
    )

    _cumulative_deficit_mm: float | None = PrivateAttr(default=None)
    """Het opgezochte maximaal cumulatief neerslagtekort [mm].

    Een privéveld en geen gewoon veld, om dezelfde reden als `_assumed_fields`: het is een
    UITKOMST van het valideren en hoort in de uitvoer thuis, niet in het invoerschema waar
    het een beller alleen maar zou verleiden het zelf te vullen.
    """

    @property
    def cumulative_deficit_mm(self) -> float | None:
        """Het cumulatief neerslagtekort waaruit `deficit_mm_per_day` is afgeleid [mm].

        `None` wanneer de beller het tekort zelf heeft opgegeven; dan is er niets opgezocht.
        """
        return self._cumulative_deficit_mm

    @model_validator(mode="after")
    def fill_deficit_defaults(self):
        """Het venster waarover het tekort wordt uitgesmeerd.

        Dertig dagen bij een tekort dat de beller zelf opgeeft, en het groeiseizoen zodra
        het uit de statistiek komt - want dat is het venster waarover die statistiek zijn
        tekort optelt. Dertig dagen zou daar 269 mm in een maand van maken, oftewel
        9 mm/dag, en dat is geen droogte maar een rekenfout.
        """
        if self.length_days is None and self.drought_statistic_choice:
            self.length_days = GROWING_SEASON_DAYS
            self._assumed_fields.add("length_days")
        else:
            self._apply_fallbacks("length_days")
        return self

    @model_validator(mode="after")
    def resolve_drought_statistic(self):
        """Zet de gekozen droogte om in een tekort per dag, of leg uit waarom dat niet kan.

        Draait NA `fill_deficit_defaults`, want het venster moet bekend zijn voordat het
        cumulatieve tekort erover verdeeld kan worden.
        """
        from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
            available_return_periods,
            cumulative_deficit_mm,
        )

        chosen = self.drought_statistic_choice
        if not chosen:
            if self.deficit_mm_per_day is None:
                raise ModelRetry(
                    "Geef het neerslagtekort op met `deficit_mm_per_day` [mm/dag], of kies "
                    "een droogte uit de statistiek met `drought_region`, "
                    "`drought_scenario` en `drought_return_period` samen. Zonder een van "
                    "die twee is er geen droogte om door te rekenen."
                )
            return self

        # dat het tripel compleet is, is hier al vastgesteld: `require_the_whole_triple`
        # draait als validator van de basisklasse en dus voor deze
        if self.deficit_mm_per_day is not None:
            raise ModelRetry(
                "Geef het tekort op EN uit de statistiek is dubbelop: "
                f"`deficit_mm_per_day`={self.deficit_mm_per_day:g} staat naast een gekozen "
                "droogte. Laat een van de twee weg, anders is niet te zien welk van beide "
                "het antwoord stuurt."
            )

        total_mm = cumulative_deficit_mm(
            self.drought_region, self.drought_scenario, self.drought_return_period
        )
        if total_mm is None:
            # Welke herhaaltijden hier WEL een waarde hebben, in plaats van een richting
            # gokken. Een null zit aan beide uiteinden: bij de natste scenario's wordt T100
            # niet gehaald en bij de droogste ligt T2 onder de reeks, dus "kies een kortere
            # herhaaltijd" is in de helft van de gevallen het verkeerde advies.
            usable = [
                period
                for period in available_return_periods()
                if cumulative_deficit_mm(
                    self.drought_region, self.drought_scenario, period
                )
                is not None
            ]
            raise ModelRetry(
                f"Voor {self.drought_region!r} in scenario {self.drought_scenario!r} is er "
                f"geen tekort bij een herhaaltijd van {self.drought_return_period} jaar: "
                "die valt buiten de reeks waarop deze statistiek is gefit. Beschikbaar zijn "
                f"hier {', '.join(str(period) for period in usable)}. Extrapoleren zou een "
                "getal verzinnen waar het rapport er geen heeft."
            )

        self._cumulative_deficit_mm = total_mm
        self.deficit_mm_per_day = total_mm / self.length_days
        return self


class SupplyWaterSystemInput(WaterSystemInput):
    """Het watersysteem plus de bruikbare diepte onder streefpeil.

    `drawdown_available_m` is verplicht en heeft bewust geen standaardwaarde, om dezelfde
    reden als `delta_h_available` op de natte kant: het is de gebiedsspecifieke grootheid
    waar het antwoord het hardst aan hangt. Met nul is er geen buffer en is elke
    niet-gedekte vraag onmiddellijk een tekort - dat is een geldig antwoord, maar het moet
    een keuze zijn en geen stilte.

    **De peilband staat hier in EEN veld en niet in twee.** De natte tools erven
    `LevelBandInput` en beschrijven de band als `[-level_margin_m, +target_level_rise_m]`
    rond het OORSPRONKELIJKE peil; de rekenkern telt die twee op tot de bufferdiepte
    (`simulate_deficit`: `drawdown_depth_m = level_margin_m + target_level_rise_m`). Aan
    de droge kant is precies die som de vraag die je aan een beheerder stelt - hoe diep mag
    het zakken voordat er schade is - en die past in een getal, gemeten vanaf het peil
    waar het gebied werkelijk op staat. Een polder die 20 cm is opgezet en daarna nog 30 cm
    mag uitzakken tot de schadegrens heeft `drawdown_available_m` = 0,50 m.

    Vandaar dat deze klasse van `WaterSystemInput` erft en niet van `LevelBandInput`: de
    twee velden erbij accepteren zou ze bovenop een getal tellen dat ze al bevat.
    """

    drawdown_available_m: float = Field(
        ...,
        ge=0,
        description=(
            "Hoe diep het peil onder het streefpeil mag zakken [m] voordat er schade "
            "optreedt. Dit is de bruikbare berging in de sloten, en gebiedsspecifiek: er "
            "is bewust geen standaardwaarde. Dynamisch peilbeheer werkt in de praktijk met "
            "0,10 tot 0,35 m; 0,35 m bleek in een proef te groot om uit te voeren. Staat "
            "het gebied al op een verhoogd streefpeil, dan zit die peilopzet HIERIN: meet "
            "vanaf het peil waar het gebied nu op staat tot de schadegrens, dus 20 cm opzet "
            "plus 30 cm uitzakking is 0,50 m. Er is aan deze kant geen apart veld voor "
            "peilopzet of peilmarge."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def refuse_the_two_field_level_band(cls, data):
        """Weiger de peilband in de vorm die de natte tools gebruiken.

        `target_level_rise_m` en `level_margin_m` bestaan hier niet, en pydantic negeert
        onbekende velden stil. Voor een beller die acht tools naast elkaar ziet is dat de
        gevaarlijkste uitkomst die er is: het veld wordt geslikt, het antwoord ziet er goed
        uit, en de peilopzet die erin stond doet niets - dezelfde faalmodus die
        `one_unit_only` op de eenheden bestrijdt.

        Weigeren en niet optellen. Optellen zou dubbeltellen: `drawdown_available_m` IS de
        som die de kern uit die twee velden maakt, dus 30 cm marge plus 20 cm opzet naast
        een opgegeven diepte van 0,50 m zou een buffer van 0,70 m opleveren.
        """
        if not isinstance(data, dict):
            return data
        given = {
            name: data[name]
            for name in ("target_level_rise_m", "level_margin_m")
            if data.get(name) is not None
        }
        if not given:
            return data

        # `:g` zoals `one_unit_only`, maar die draait NA de coercie en deze ervoor: hier
        # kan er nog een string of onzin in staan, en dan hoort er een uitleg uit te komen
        # en geen format-fout.
        def shown(value):
            try:
                return f"{float(value):g}"
            except (TypeError, ValueError):
                return repr(value)

        listed = " en ".join(
            f"`{name}`={shown(value)}" for name, value in given.items()
        )
        belong = "horen" if len(given) > 1 else "hoort"
        raise ModelRetry(
            f"De aanvoertools kennen de peilband als een veld: {listed} {belong} hier in "
            "`drawdown_available_m`. Dat is de hele diepte onder het streefpeil waar het "
            "gebied nu op staat - peilopzet en peilmarge samen - dus tel ze op: 20 cm "
            "opzet plus 30 cm marge is drawdown_available_m=0.5. Ze naast elkaar "
            "doorgeven zou ze dubbel tellen."
        )

    # De BESTAANDE inlaat, en dus context en geen maatregel - precies zoals
    # `discharge_capacity_*` op de natte kant het bestaande gemaal is en
    # `delta_discharge_capacity_*` de uitbreiding. Zonder dit veld kon geen van beide
    # aanvoertools een polder doorrekenen die al een inlaat heeft, en betekende
    # `measure.delta` in de twee tools iets verschillends: bij `..._given_h` "wat er bij
    # moet" en bij `..._given_supply` nul, omdat de opgegeven inlaat daar als bestaande
    # situatie werd gelezen. Nu vraagt de tool naar allebei en is het antwoord ondubbelzinnig.
    supply_capacity_m3_per_sec: float | None = Field(
        None,
        ge=0,
        description=(
            "BESTAANDE inlaatcapaciteit [m3/s]. Laat weg als het gebied er geen heeft - dat "
            "is de normale situatie, en dan is `measure.before` nul. Gangbaar is de "
            "aanvoernorm van 0,3 tot 0,4 l/s/ha, ruim een orde kleiner dan een gemaal."
        ),
    )
    supply_capacity_m3_per_min: float | None = Field(
        None, ge=0, description="Bestaande inlaatcapaciteit [m3/min]."
    )
    supply_capacity_m3_per_day: float | None = Field(
        None, ge=0, description="Bestaande inlaatcapaciteit [m3/dag]."
    )
    supply_capacity_mm_d: float | None = Field(
        None, ge=0, description="Bestaande inlaatcapaciteit [mm/dag]."
    )
    supply_capacity_l_s_ha: float | None = Field(
        None,
        ge=0,
        description=(
            "Bestaande inlaatcapaciteit [l/s/ha]. De aanvoernorm is 0,3 tot 0,4 l/s/ha; "
            "dit is de eenheid waarin die norm wordt uitgedrukt."
        ),
    )

    @model_validator(mode="after")
    def validate_existing_supply_capacity(self):
        """Vul de vijf velden uit de ene die is opgegeven, of zet ze op nul.

        Nul is hier de juiste stilte en geen aanname die gemeld moet worden: een polder
        heeft standaard geen inlaat, en dat is precies wat `measure.before` toch al zegt.
        """
        one_unit_only(
            "de bestaande inlaatcapaciteit",
            supply_capacity_m3_per_sec=self.supply_capacity_m3_per_sec,
            supply_capacity_m3_per_min=self.supply_capacity_m3_per_min,
            supply_capacity_m3_per_day=self.supply_capacity_m3_per_day,
            supply_capacity_mm_d=self.supply_capacity_mm_d,
            supply_capacity_l_s_ha=self.supply_capacity_l_s_ha,
        )
        m3_per_sec = (
            discharge_capacity_to_m3_per_sec(
                m3_per_sec=self.supply_capacity_m3_per_sec,
                m3_per_min=self.supply_capacity_m3_per_min,
                m3_per_day=self.supply_capacity_m3_per_day,
                mm_d=self.supply_capacity_mm_d,
                l_s_ha=self.supply_capacity_l_s_ha,
                area_m2=self.area_m2,
            )
            or 0.0
        )
        units = discharge_capacity_in_all_units(m3_per_sec, self.area_m2)
        self.supply_capacity_m3_per_sec = units["m3_per_sec"]
        self.supply_capacity_m3_per_min = units["m3_per_min"]
        self.supply_capacity_m3_per_day = units["m3_per_day"]
        self.supply_capacity_mm_d = units["mm_d"]
        self.supply_capacity_l_s_ha = units["l_s_ha"]
        return self


class SupplyInputGivenH(DeficitInput, SupplyWaterSystemInput):
    """Invoer voor de inverse vraag: hoeveel inlaatcapaciteit is er nodig?

    Aanvoeren = supply.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_l_s_ha": 1.25,
                "deficit_mm_per_day": 4,
                "drawdown_available_m": 0.3,
            }
        }
    )


# Waarom twee inlaatvelden en niet een. Er was alleen `supply_capacity_*`, en de opgegeven
# waarde werd als de BESTAANDE situatie gelezen: `measure.delta` meldde dan nul terwijl er
# een inlaat van 1,2 m3/s in het spel was die 50 van de 120 mm levert. Een beller die
# `measure.delta` leest als "wat moet er gebeuren" - bij de zeven andere maatregeltools de
# juiste lezing - concludeerde daaruit dat er niets hoeft te gebeuren.
#
# Deze uitleg staat bewust in een comment en niet in de docstring hieronder: die docstring
# is de beschrijving van het INVOERSCHEMA en wordt door een agent gelezen voordat hij ooit
# een aanroep heeft gedaan. Wat er ooit anders was helpt hem daar niet; het kost alleen
# ruimte in het veld dat hem moet vertellen wat hij invult.
class SupplyInputGivenSupply(DeficitInput, SupplyWaterSystemInput):
    """Invoer voor de voorwaartse vraag: wat doet deze extra inlaatcapaciteit?

    Aanvoeren = supply.

    Twee inlaatvelden en niet een, precies zoals het afvoerpaar: `supply_capacity_*` is de
    inlaat die er al ligt en `delta_supply_capacity_*` is wat je erbij legt. Heeft het
    gebied nog geen inlaat, laat het eerste dan weg - dan is `measure.before` nul en is
    `measure.delta` gewoon de inlaat die je doorrekent.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_l_s_ha": 1.25,
                "deficit_mm_per_day": 4,
                "drawdown_available_m": 0.3,
                "delta_supply_capacity_l_s_ha": 0.4,
            }
        }
    )

    delta_supply_capacity_m3_per_sec: float | None = Field(
        None,
        ge=0,
        description=(
            "EXTRA inlaatcapaciteit [m3/s], boven op `supply_capacity_m3_per_sec`. Heeft "
            "het gebied nog geen inlaat, dan is dit gewoon de inlaat die je doorrekent. "
            "Gangbaar is de aanvoernorm van 0,3 tot 0,4 l/s/ha, oftewel 0,03 tot 0,04 m3/s "
            "per 100 ha - ruim een orde kleiner dan een gemaal."
        ),
    )
    delta_supply_capacity_m3_per_min: float | None = Field(
        None,
        ge=0,
        description=(
            "Extra inlaatcapaciteit [m3/min]. Gangbaar is 0,3 tot 0,4 l/s/ha, oftewel "
            "1,8 tot 2,4 m3/min per 100 ha."
        ),
    )
    delta_supply_capacity_m3_per_day: float | None = Field(
        None,
        ge=0,
        description=(
            "Extra inlaatcapaciteit [m3/dag]. Gangbaar is 0,3 tot 0,4 l/s/ha, oftewel "
            "2600 tot 3500 m3/dag per 100 ha."
        ),
    )
    delta_supply_capacity_mm_d: float | None = Field(
        None,
        ge=0,
        description=(
            "Extra inlaatcapaciteit [mm/dag]. Gangbaar is 0,3 tot 0,4 l/s/ha, oftewel "
            "2,6 tot 3,5 mm/dag. Handig omdat het tekort in dezelfde eenheid staat: een "
            "inlaat van 3,5 mm/dag dekt een tekort van 3,5 mm/dag."
        ),
    )
    delta_supply_capacity_l_s_ha: float | None = Field(
        None,
        ge=0,
        description=(
            "Extra inlaatcapaciteit [l/s/ha]. De aanvoernorm is 0,3 tot 0,4 l/s/ha; dit is "
            "de eenheid waarin die norm wordt uitgedrukt, dus meestal de makkelijkste."
        ),
    )

    @model_validator(mode="after")
    def validate_delta_supply_capacity(self):
        """Vul de vijf delta-velden uit de ene die is opgegeven.

        Zelfde conversie als bij het gemaal, maar zonder negatieve tak: een inlaat de
        andere kant op is een gemaal, en dat is een eigen veld.
        """
        one_unit_only(
            "de extra inlaatcapaciteit",
            delta_supply_capacity_m3_per_sec=self.delta_supply_capacity_m3_per_sec,
            delta_supply_capacity_m3_per_min=self.delta_supply_capacity_m3_per_min,
            delta_supply_capacity_m3_per_day=self.delta_supply_capacity_m3_per_day,
            delta_supply_capacity_mm_d=self.delta_supply_capacity_mm_d,
            delta_supply_capacity_l_s_ha=self.delta_supply_capacity_l_s_ha,
        )
        m3_per_sec = discharge_capacity_to_m3_per_sec(
            m3_per_sec=self.delta_supply_capacity_m3_per_sec,
            m3_per_min=self.delta_supply_capacity_m3_per_min,
            m3_per_day=self.delta_supply_capacity_m3_per_day,
            mm_d=self.delta_supply_capacity_mm_d,
            l_s_ha=self.delta_supply_capacity_l_s_ha,
            area_m2=self.area_m2,
        )
        if m3_per_sec is None:
            raise ModelRetry(
                "Geef de extra inlaatcapaciteit op in een van deze eenheden: "
                "delta_supply_capacity_l_s_ha, delta_supply_capacity_m3_per_sec, "
                "delta_supply_capacity_m3_per_min, delta_supply_capacity_m3_per_day of "
                "delta_supply_capacity_mm_d. Bedoel je de inlaat die er al ligt, dan is dat "
                "supply_capacity_l_s_ha."
            )
        units = discharge_capacity_in_all_units(m3_per_sec, self.area_m2)
        self.delta_supply_capacity_m3_per_sec = units["m3_per_sec"]
        self.delta_supply_capacity_m3_per_min = units["m3_per_min"]
        self.delta_supply_capacity_m3_per_day = units["m3_per_day"]
        self.delta_supply_capacity_mm_d = units["mm_d"]
        self.delta_supply_capacity_l_s_ha = units["l_s_ha"]
        return self


class SupplyOutput(EngineerOutputModel):
    """Uitvoer van de maatregel aanvoeren.

    Bewust géén `MeasureOutput`. Die is opgebouwd rond de maximale waterstand*stijging* en
    haar haalbare bereik, en op de droogtekant bestaan die grootheden niet: er is geen
    stijging, er is een uitzakking en een volume vraag dat onvervuld blijft. Een gedeeld
    uitvoermodel zou vier velden leeg laten en drie velden een andere betekenis geven, en
    dat is precies de soort dubbelzinnigheid die WP6 heeft opgeruimd.
    """

    data: dict = Field(..., description="Ruwe uitkomsten en tussenresultaten")
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
            "exact = de benodigde capaciteit is bepaald; no_measure_needed = de eigen "
            "berging dekt het tekort al; action_infeasible = zelfs de maximale "
            "inlaatcapaciteit die deze tool onderzoekt dekt het niet"
        ),
    )
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description=(
            "Standaardwaarden waarmee gerekend is omdat ze niet zijn opgegeven. Leeg als "
            "de beller alles heeft ingevuld"
        ),
    )
    sensitivity: list[Sensitivity] = Field(
        default_factory=list,
        description=(
            "Per aangenomen veld het antwoord aan de uiteinden van zijn plausibele bereik"
        ),
    )
    caveats: list[ModelCaveat] = Field(
        default_factory=list,
        description=(
            "Structurele beperkingen die op dit antwoord van toepassing zijn. Voor "
            "aanvoeren is de belangrijkste dat dit een antwoord over CAPACITEIT is en dat "
            "de beschikbaarheid van het water buiten dit model valt"
        ),
    )

    priceless: list[PricelessPost] = Field(
        default_factory=list,
        description=(
            "Aanvoeren heeft geen prijs, en dat is niet hetzelfde als gratis. Er staat "
            "daarom geen `cost` in deze uitvoer maar wel deze lijst, met waar de prijs uit "
            "bestaat: het water en niet het kunstwerk. Noem hem in je terugkoppeling"
        ),
    )

    measure: MeasureChange = Field(
        ...,
        description=(
            "Wat de inlaat met het systeem doet: van welke capaciteit naar welke, en "
            "hoeveel dat is. `before` is vaak nul - een polder heeft standaard geen inlaat "
            "- en dan is `delta_relative` `None`"
        ),
    )
    supply_capacity_m3_per_sec: float = Field(
        ..., description="De inlaatcapaciteit waar dit antwoord bij hoort [m3/s]"
    )
    demand_mm: float = Field(
        ...,
        description=(
            "Totale watervraag over de periode [mm over de polder]: het tekort per dag "
            "maal het aantal dagen"
        ),
    )
    supplied_mm: float = Field(
        ..., description="Wat de inlaat over de periode heeft geleverd [mm]"
    )
    buffer_mm: float = Field(
        ...,
        description=(
            "Wat uit de eigen berging onder streefpeil is gekomen [mm]. Dit is de "
            "drooglegging die je inzet: peilmarge maal het aandeel open water"
        ),
    )
    shortfall_mm: float = Field(
        ...,
        description=(
            "Vraag die noch de inlaat noch de berging kon dekken [mm]. Nul betekent dat "
            "het streefpeil de hele periode gehouden wordt"
        ),
    )
    drawdown_m: float = Field(
        ...,
        description=(
            "Hoe diep het peil onder het streefpeil is gezakt [m], positief gerekend. "
            "Begrensd door drawdown_available_m"
        ),
    )
    days_until_buffer_empty: float | None = Field(
        None,
        description=(
            "Na hoeveel dagen de eigen berging op is [dagen]; null als dat binnen de "
            "periode niet gebeurt. Vaak de bruikbaarste uitlezing van de drie, omdat een "
            "aantal dagen makkelijker af te wegen is dan een aantal millimeters"
        ),
    )
    available_source_volume_m3: float | None = Field(
        None,
        description=(
            "Het bronvolume waarmee gerekend is [m3]; null als er met een onbeperkte bron "
            "is gerekend. Komt het uit de statistiek, dan staat in `data.source_statistic` "
            "hoe het is opgebouwd"
        ),
    )
    source_volume_used_m3: float = Field(
        ...,
        description=(
            "Wat er over de periode door de inlaat is gegaan [m3]. Het volume en niet het "
            "debiet, want een bron is eindig in volume: 0,45 l/s/ha klinkt als een pompje, "
            "4,7 miljoen m3 in een maand is een vraag aan het regionale systeem"
        ),
    )
    days_until_source_empty: float | None = Field(
        None,
        description=(
            "Na hoeveel dagen de BRON leeg is [dagen]; null als hij het houdt of onbeperkt "
            "is. De tegenhanger van `days_until_buffer_empty`, en het onderscheid is het "
            "punt: de eigen berging koopt tijd, de bron bepaalt of er iets te kopen is"
        ),
    )

    @model_serializer(mode="wrap")
    def _round_output(self, handler):
        """Rond de hele uitvoer af op significante cijfers; zie SIGNIFICANT_DIGITS."""
        return round_floats(handler(self))
