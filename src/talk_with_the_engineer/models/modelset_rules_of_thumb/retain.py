from pydantic import ConfigDict, Field, model_validator
from typing import Union

from pydantic_ai import ModelRetry


from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    LevelBandInput,
    hide_null_branch_and_bound,
    one_unit_only,
)


def refuse_a_negative_delay(days) -> None:
    """Weiger een negatieve vertraging met uitleg in plaats van met een validatiedump.

    Zonder deze regel loopt de waarde door tot in `PolderState`, en dan lekt de ruwe
    pydantic-fout naar de aanroeper: een interne klassenaam, een veldnaam die niet is wat hij
    invulde, in het Engels, met een verwijzing naar errors.pydantic.dev. Dat is voor een
    waterbeheerder geen handelingsperspectief.
    """
    if days is not None and days < 0:
        raise ModelRetry(
            f"days_to_retain_discharge is het aantal EXTRA dagen dat de afvoer wordt "
            f"vertraagd en kan niet negatief zijn; er staat {days}. Nul betekent geen "
            "vertraging, en dat is de ondergrens - afvoer versnellen is in dit model geen "
            "maatregel. Wil je weten wat vasthouden zonder vertraging doet, geef dan 0."
        )


class RetentionInputGivenH(RainfallInput, LevelBandInput):
    """
    Input model for Retention tool.
    Requires return periods to be specified.

    Retention = Vasthouden
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "delta_h_available": 1.0,
            }
        }
    )

    # Everything for rainfall is inherited from RainfallInput
    # Rest of the calculation:
    days_to_retain_discharge: int | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(0),
        description=(
            "Aantal extra dagen dat het water op het land wordt vastgehouden. Kan niet "
            "negatief zijn; nul betekent geen vertraging. Weet je dit niet, laat het veld "
            "dan weg in plaats van het te schatten; de tool rekent met 2 dagen en meldt "
            "dat in `assumptions`"
        ),
    )

    @model_validator(mode="after")
    def fill_retention_defaults(self):
        refuse_a_negative_delay(self.days_to_retain_discharge)
        self._apply_fallbacks("days_to_retain_discharge")
        return self

    delta_h_available: float = Field(
        ...,
        gt=0,
        description=(
            "Waterstandstijging die het gebied nog aankan [m]; het doel waarop de "
            "maatregel wordt gedimensioneerd. Dit is de drooglegging tot het maaiveld "
            "van het laagste te beschermen perceel, dus gebiedsspecifiek: er is bewust "
            "geen standaardwaarde. Ordegrootte 0,2 tot 1,0 m."
        ),
    )


class RetentionInputGivenArea(RainfallInput, LevelBandInput):
    """
    Input model for Retention tool.
    Requires return periods to be specified.

    Retention = Vasthouden
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "delta_area_ha": 1158,
            }
        }
    )

    days_to_retain_discharge: int | None = Field(
        None,
        json_schema_extra=hide_null_branch_and_bound(0),
        description=(
            "Aantal extra dagen dat het water op het land wordt vastgehouden. Kan niet "
            "negatief zijn; nul betekent geen vertraging. Weet je dit niet, laat het veld "
            "dan weg in plaats van het te schatten; de tool rekent met 2 dagen en meldt "
            "dat in `assumptions`"
        ),
    )

    @model_validator(mode="after")
    def fill_retention_defaults(self):
        refuse_a_negative_delay(self.days_to_retain_discharge)
        self._apply_fallbacks("days_to_retain_discharge")
        return self

    # De beschrijving zei "positive for increase, negative for decrease" en de tool weigerde
    # een negatieve waarde. Het schema nodigde dus uit tot een aanroep die per definitie
    # faalt, en een beller die de veldbeschrijving serieus nam liep daar vroeg of laat
    # tegenaan.
    #
    # De ondergrens staat nu in het schema - `minimum: 0`, zodat een client hem ziet
    # voordat hij de aanroep verstuurt - maar niet als `ge=0`. Een pydantic-constraint
    # levert aan de MCP-grens een rauwe validatiefout op, met `[type=greater_than_equal]`
    # en een link naar errors.pydantic.dev erin. De handhaving zit daarom in
    # `validate_area_available`, met een melding in de stijl van de rest van dit systeem:
    # weiger, leg uit, en wijs een kant op.
    delta_area_ha: float | None = Field(
        None,
        json_schema_extra={"minimum": 0},
        description=(
            "Areaal dat voor retentie wordt ingericht [ha]: land waarvan de afvoer wordt "
            "vertraagd. Kan niet negatief zijn - dit is de maatvoering van de maatregel en "
            "niet een verandering ten opzichte van bestaande retentie."
        ),
    )
    delta_area_m2: float | None = Field(
        None,
        json_schema_extra={"minimum": 0},
        description=(
            "Areaal dat voor retentie wordt ingericht [m2]. Kan niet negatief zijn; zie "
            "delta_area_ha."
        ),
    )

    @model_validator(mode="after")
    def validate_area_available(self):
        one_unit_only(
            "het retentie-areaal",
            delta_area_ha=self.delta_area_ha,
            delta_area_m2=self.delta_area_m2,
        )
        for name in ("delta_area_ha", "delta_area_m2"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ModelRetry(
                    f"{name} is het areaal dat voor retentie wordt ingericht en kan niet "
                    "negatief zijn. Bedoel je minder retentie dan er nu ligt, geef dan het "
                    "kleinere areaal op; vasthouden opheffen is in dit model geen maatregel."
                )
        if self.delta_area_ha is not None:
            self.delta_area_m2 = self.delta_area_ha * 10000
        elif self.delta_area_m2 is not None:
            self.delta_area_ha = self.delta_area_m2 / 10000
        else:
            raise ModelRetry(
                "Geef het retentie-areaal op in een van deze eenheden: delta_area_ha of "
                "delta_area_m2. Dat is het land waarvan de afvoer wordt vertraagd."
            )
        return self


class RetentionOutput(MeasureOutput):
    """Uitvoer van de maatregel; velden komen uit MeasureOutput."""


# Type alias for utility functions
RetentionInput = Union[RetentionInputGivenH, RetentionInputGivenArea]
