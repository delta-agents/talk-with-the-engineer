"""De bui als toolinvoer: het exogene deel van een aanroep.

Dit is de INTERFACE-kant van `E`. Wat er over de draad komt: met een taal erbij, met een
boekhouding van welke velden zijn aangenomen, en met de validatie die een aanroeper een
begrijpelijke fout geeft. `to_storm()` levert de kernvorm, en die weet van niets daarvan.
"""

from typing import Literal

from pydantic import Field, model_validator
from pydantic_ai import ModelRetry

from talk_with_the_engineer.core.exogenous import Storm
from talk_with_the_engineer.interface.schemas.base import (
    AssumedDefaults,
    hide_null_branch,
)

# Alle gegeven zijn overgenomen uit tabel 6 en 7 in deelrapport 3 (regionale statistiek voor extreme neerslag) van STOWA-2019

RETURN_PERIODS = [
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    25.0,
    50.0,
    100.0,
    200.0,
    250.0,
    500.0,
    1000.0,
]

LENGTH_EVENT_HRS = [
    48.0,
    96.0,
    192.0,
]

TIME_OF_YEAR = [
    "winter",
    "summer",
]

RAINFALL_REGIMES = ["LL", "L", "R", "H"]

NAME_RAINFALL_PATTERN = ["p_0", "p1a", "p1b", "p1c", "p1d", "p2a", "p2b"]


class RainfallInput(AssumedDefaults):
    """De bui: het exogene deel van de invoer.

    De toegestane waarden staan als `Literal` in het type en dus als `enum` in het
    JSON-schema, met de constantenlijsten hierboven als enige bron. Dat is wat een MCP-client
    nodig heeft om ze te kunnen valideren: staan ze alleen als tekst in de veldbeschrijving
    en worden ze door een validator afgedwongen, dan kan een model dat op het schema wordt
    gestuurd nog steeds een ongeldige waarde genereren.
    """

    return_period: Literal[*RETURN_PERIODS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Terugkeertijd van de bui in jaren; 0.5 betekent gemiddeld twee keer per jaar. "
            "De tool zoekt de neerslagsom er dan bij in de STOWA-statistiek. Geef deze OF "
            "`rain_volume_mm` op - een van de twee is verplicht en allebei tegelijk wordt "
            "geweigerd."
        ),
    )
    rain_volume_mm: float | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "De neerslagsom van de bui [mm], als je hem zelf opgeeft in plaats van hem uit "
            "de statistiek te laten halen - een gemeten bui, een bui uit een ander rapport, "
            "of een hypothese. Dit is de BRUTO som over de hele bui: het neerslagverlies "
            "gaat er in de zomer nog vanaf. Ter ijking: de statistiek geeft voor 96 uur in "
            "de zomer 59 mm bij T10 en 87 mm bij T100. De duur, de vorm en het seizoen "
            "blijven gewoon gelden - `length_event_hrs` bepaalt over hoeveel dagen deze som "
            "wordt verdeeld en `name_rainfall_pattern` hoe. Geef deze OF `return_period` "
            "op; `rainfall_regime` vervalt hierbij, want dat is een correctie op de "
            "opgezochte som."
        ),
    )
    time_of_year: Literal[*TIME_OF_YEAR] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Halfjaar waarvoor de neerslagstatistiek geldt. Let op: 'summer' gebruikt de "
            "jaarrondstatistiek als benadering van de zomer. Weet je dit niet, laat het veld "
            "dan weg in plaats van het te schatten; de tool rekent met 'summer' en meldt "
            "dat in `assumptions`"
        ),
    )
    length_event_hrs: Literal[*LENGTH_EVENT_HRS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Duur van de bui in uren: 48, 96 of 192, oftewel 2, 4 of 8 dagen. Vul uren in; "
            "de uitvoer meldt hem in dagen. Weet je dit niet, laat het veld dan weg in "
            "plaats van het te schatten; de tool rekent met 96 uur (4 dagen) en meldt dat "
            "in `assumptions`"
        ),
    )
    rainfall_regime: Literal[*RAINFALL_REGIMES] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Neerslagregime van het gebied: LL en L voor weinig regionale spreiding, "
            "R als referentie, H voor veel spreiding. Weet je dit niet, laat het veld dan "
            "weg in plaats van het te schatten; de tool rekent met 'R' en meldt dat in "
            "`assumptions`"
        ),
    )
    name_rainfall_pattern: Literal[*NAME_RAINFALL_PATTERN] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Naam van het neerslagpatroon binnen de bui. Weet je dit niet, laat het veld "
            "dan weg in plaats van het te schatten; de tool rekent met 'p1c' en meldt dat "
            "in `assumptions`"
        ),
    )

    @model_validator(mode="after")
    def require_one_source_for_the_rainfall_total(self):
        """De bui komt uit de statistiek of van de beller, en niet uit allebei.

        Dezelfde vorm als op de droge kant, waar `deficit_mm_per_day` en het droogtetripel
        elkaar uitsluiten: twee ingangen naast elkaar maakt onzichtbaar welke van de twee
        het antwoord stuurt.
        """
        if self.return_period is not None and self.rain_volume_mm is not None:
            raise ModelRetry(
                "De neerslagsom opgeven EN uit de statistiek halen is dubbelop: "
                f"`rain_volume_mm`={self.rain_volume_mm:g} staat naast "
                f"`return_period`={self.return_period:g}. Laat een van de twee weg, anders "
                "is niet te zien welk van beide het antwoord stuurt."
            )
        if self.return_period is None and self.rain_volume_mm is None:
            raise ModelRetry(
                "Geef de bui op: `return_period` als je hem uit de STOWA-statistiek wilt "
                "laten halen, of `rain_volume_mm` als je de neerslagsom zelf hebt. Zonder "
                "een van die twee is er geen bui om door te rekenen."
            )
        return self

    @model_validator(mode="after")
    def fill_rainfall_defaults(self):
        self.apply_fallbacks(
            "time_of_year",
            "length_event_hrs",
            "rainfall_regime",
            "name_rainfall_pattern",
        )
        return self

    @model_validator(mode="after")
    def refuse_a_regime_that_cannot_apply(self):
        """`rainfall_regime` is een correctiefactor OP de opgezochte som.

        Geeft de beller de som zelf, dan is er niets meer om te corrigeren: de factor zou
        zijn gemeten of gekozen getal verschuiven met tot 9 %, en dat is precies het soort
        stille wijziging dat de rest van dit systeem weigert. Draait na
        `fill_rainfall_defaults`, zodat `assumed_fields` weet of de beller hem zelf invulde.
        """
        if self.rain_volume_mm is None:
            return self
        if "rainfall_regime" not in self._assumed_fields:
            raise ModelRetry(
                f"`rainfall_regime`={self.rainfall_regime!r} werkt niet samen met "
                "`rain_volume_mm`: het regime is een correctiefactor op de neerslagsom die "
                "de tool OPZOEKT, en die zoekt hij hier niet op. Laat het regime weg, of "
                "verwerk het zelf in de som die je opgeeft."
            )
        # niet aangenomen maar niet van toepassing: hem in `assumptions` melden zou
        # suggereren dat hij dit antwoord stuurt
        self._assumed_fields.discard("rainfall_regime")
        return self

    def to_storm(self) -> Storm:
        """De bui in de vorm die de rekenkern aanneemt.

        De enige plek waar een aanroep in een `Storm` verandert. Alles wat hier niet in
        meegaat - de taal, welke velden zijn aangenomen, de twee validators - hoort bij de
        aanroep en niet bij het weer; de kern kan er niets mee en zou eraan gaan hangen.

        De validators draaien voor deze omzetting, dus wat hier langskomt heeft precies een
        bron voor zijn neerslagsom en een regime dat van toepassing is. `Storm.__post_init__`
        controleert dat nog eens, voor aanroepers die de kern direct gebruiken.
        """
        return Storm(
            time_of_year=self.time_of_year,
            length_event_hrs=self.length_event_hrs,
            name_rainfall_pattern=self.name_rainfall_pattern,
            rainfall_regime=self.rainfall_regime,
            return_period=self.return_period,
            rain_volume_mm=self.rain_volume_mm,
        )
