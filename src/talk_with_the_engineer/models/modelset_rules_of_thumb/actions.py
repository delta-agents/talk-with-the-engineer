"""Maatregelen als getypeerde acties op de polder-toestand.

Dit is het `a` uit `s' = f(s, a, w)`. Elke maatregel raakt precies een toestandsveld, en
draagt zijn eigen eenheid en prijs. De eenheden zijn niet uitwisselbaar: bij bergen wordt
land gekocht, bij vasthouden het recht om het af en toe onder water te zetten.

De eenheidskosten hieronder zijn onderbouwd met Nederlandse projecten en statistieken;
elke `UnitCost` draagt zijn eigen bron. Zie PLAN_TOOLS_REFACTOR.md §8.1 voor de volledige
verantwoording, inclusief wat er buiten deze getallen valt.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState

# Afvoeren heeft geen harde fysieke bovengrens. Dit plafond bestaat zodat een onhaalbaar
# doel in een eindige zoekruimte blijft en als `physical_upper_bound` gemeld wordt.
MAX_PUMP_FACTOR = 20.0

SECONDS_PER_MINUTE = 60


class UnitCost(BaseModel):
    """Eenheidskosten met bandbreedte en herkomst.

    De bandbreedte staat erbij omdat een enkel getal hier valse precisie zou zijn: de
    grondprijs schommelde in 2025 van 85.300 naar boven de 100.000 euro per hectare en
    verschilt regionaal een factor drie. Reken daarom met `low` en `high` zodra het
    antwoord ergens op gebaseerd wordt.
    """

    model_config = ConfigDict(frozen=True)

    typical: float = Field(..., gt=0, description="Werkwaarde [EUR per eenheid]")
    low: float = Field(..., gt=0, description="Ondergrens van de bandbreedte")
    high: float = Field(..., gt=0, description="Bovengrens van de bandbreedte")
    unit: str = Field(..., description="Waar de prijs per eenheid van is")
    price_level: str = Field(..., description="Prijspeil, bijvoorbeeld '2024/25'")
    source: str = Field(..., description="Waar deze getallen vandaan komen")


# Grondverwerving 86.400 EUR/ha grasland tot 106.700 EUR/ha bouwland (Kadaster/NVM,
# gemiddeld 95.400 over 2025), plus grondwerk. Het enige projectcijfer inclusief grond dat
# we vonden is Blauwe Poort in Laarbeek: 3,4 mln voor 15 ha, dus 227.000 EUR/ha - maar dat
# is kleinschalig en vermoedelijk een bovengrens. Dit is de dunst onderbouwde van de drie.
COST_OPEN_WATER = UnitCost(
    typical=135_000,
    low=120_000,
    high=230_000,
    price_level="2024/25",
    unit="EUR per ha open water",
    source=(
        "Kadaster/NVM agrarische grondprijzen 2025 plus grondwerk; projectreferentie "
        "Blauwe Poort Laarbeek (15 ha, 3,4 mln incl. grond)"
    ),
)

# Twee onafhankelijke gemaalprojecten uit 2024/25 komen binnen 10 % van elkaar uit per
# eenheid geinstalleerd vermogen: De Poel (Scheldestromen) 9,1 mln voor 270 m3/min is
# 33.700, en Galgenrak (Drents Overijsselse Delta) 16,9 mln voor 550 m3/min is 30.700.
# Uitgedrukt per m3/s omdat dat de eenheid van de actie is.
COST_PUMP_CAPACITY = UnitCost(
    typical=32_000 * SECONDS_PER_MINUTE,
    low=31_000 * SECONDS_PER_MINUTE,
    high=34_000 * SECONDS_PER_MINUTE,
    price_level="2024/25",
    unit="EUR per m3/s",
    source=(
        "gemaal De Poel (9,1 mln / 270 m3/min) en gemaal Galgenrak "
        "(16,9 mln / 550 m3/min)"
    ),
)

# Aanlegkosten van peilgestuurde drainage: 2.400 EUR/ha voor een volledig nieuw systeem,
# 1.250 EUR/ha als het op bestaande conventionele drainage wordt aangesloten.
# Waterschapssubsidies dekken 400 tot 3.000 EUR/ha, wat de bandbreedte bevestigt.
COST_RETENTION = UnitCost(
    typical=2_400,
    low=1_250,
    high=3_000,
    price_level="~2020",
    unit="EUR per ha land",
    source="aanlegkosten peilgestuurde drainage (STOWA, Waterschap Rivierenland)",
)


class Action(BaseModel, ABC):
    """Een maatregel met maatvoering."""

    model_config = ConfigDict(frozen=True)

    name_nl: ClassVar[str]
    name_en: ClassVar[str]
    unit: ClassVar[str]

    unit_cost: UnitCost | None = Field(
        None, description="Eenheidskosten; None schakelt de kostenberekening uit"
    )

    @property
    @abstractmethod
    def magnitude(self) -> float:
        """De maatvoering, in `unit`."""

    @abstractmethod
    def at(self, magnitude: float) -> "Action":
        """Dezelfde maatregel met een andere maatvoering."""

    @abstractmethod
    def apply(self, state: PolderState) -> PolderState:
        """De toestand na uitvoering van deze maatregel."""

    @abstractmethod
    def upper_bound(self, state: PolderState) -> float:
        """De grootste maatvoering die in deze toestand mogelijk is."""

    def chargeable_quantity(self, state: PolderState) -> float:
        """Waarover de eenheidsprijs gerekend wordt.

        Standaard de maatvoering zelf: bergen en vasthouden zijn lineair in het areaal.
        Afvoeren wijkt af, zie `AfvoerenAction`.
        """
        return self.magnitude

    def cost(self, state: PolderState) -> float | None:
        """Investeringskosten [EUR]. Geen exploitatie, zie PLAN_TOOLS_REFACTOR.md §8.1."""
        if self.unit_cost is None:
            return None
        return self.unit_cost.typical * self.chargeable_quantity(state)

    def cost_range(self, state: PolderState) -> tuple[float, float] | None:
        """Onder- en bovengrens van de investeringskosten [EUR]."""
        if self.unit_cost is None:
            return None
        quantity = self.chargeable_quantity(state)
        return self.unit_cost.low * quantity, self.unit_cost.high * quantity


class BergenAction(Action):
    """Bergen: land wordt open water. Verhoogt `pct_open_water`."""

    name_nl: ClassVar[str] = "bergen"
    name_en: ClassVar[str] = "store"
    unit: ClassVar[str] = "ha open water"

    delta_open_water_ha: float = Field(0.0, ge=0.0)
    unit_cost: UnitCost | None = COST_OPEN_WATER

    @property
    def magnitude(self) -> float:
        return self.delta_open_water_ha

    def at(self, magnitude: float) -> "BergenAction":
        return BergenAction(delta_open_water_ha=magnitude, unit_cost=self.unit_cost)

    def apply(self, state: PolderState) -> PolderState:
        new_open_water_ha = state.area_open_water_ha + self.delta_open_water_ha
        return state.replace(pct_open_water=new_open_water_ha / state.area_ha * 100.0)

    def upper_bound(self, state: PolderState) -> float:
        # al het resterende land kan in principe open water worden
        return max(state.area_ha - state.area_open_water_ha, 0.0)


class AfvoerenAction(Action):
    """Afvoeren: meer gemaalcapaciteit. Verhoogt `pump_capacity_m3_per_sec`.

    **De kosten worden lineair in de toename gerekend, en dat is een bewuste
    vuistregelvereenvoudiging.** In werkelijkheid is een gemaal een trapkost: je koopt een
    gemaal, niet een m3/min. Beide projecten waarop het tarief rust zijn volledige
    vervangingen - De Poel kocht 50 m3/min extra voor 9,1 mln, Galgenrak 210 m3/min extra
    voor 16,9 mln - dus per eenheid *extra* vermogen kostten ze 182.000 en 80.000 EUR per
    m3/min, tegen 31.000 tot 34.000 per eenheid *geinstalleerd* vermogen.

    Lineair rekenen onderschat de kosten van een kleine uitbreiding daarom sterk. Op de
    referentiepolder is een norm van 100 cm lineair 5,6 mln en als vervanging 15,2 mln.

    Het gevolg voor de uitkomst is niet klein: lineair is afvoeren bij elke ambitie de
    goedkoopste maatregel, terwijl er met de trapkost een omslagpunt rond 100 cm ontstaat
    waaronder bergen goedkoper is. De conclusie "altijd pompen" volgt dus uit deze
    aanname en niet uit de hydrologie. Zie PLAN_TOOLS_REFACTOR.md §8.1.

    `replacement_quantity` geeft de trapkost-lezing, zodat de afwijking na te rekenen is.
    """

    name_nl: ClassVar[str] = "afvoeren"
    name_en: ClassVar[str] = "discharge"
    unit: ClassVar[str] = "m3/s"

    delta_pump_capacity_m3_per_sec: float = Field(0.0, ge=0.0)
    unit_cost: UnitCost | None = COST_PUMP_CAPACITY

    @property
    def magnitude(self) -> float:
        return self.delta_pump_capacity_m3_per_sec

    def at(self, magnitude: float) -> "AfvoerenAction":
        return AfvoerenAction(
            delta_pump_capacity_m3_per_sec=magnitude, unit_cost=self.unit_cost
        )

    def replacement_quantity(self, state: PolderState) -> float:
        """De nieuwe totale capaciteit; de trapkost-lezing van de prijs.

        Niet gebruikt in `cost`, want dat rekent bewust lineair. Zie de klasse-docstring:
        deze methode maakt de afwijking meetbaar in plaats van alleen beschreven, en
        `test_discharge_cost_is_linear_by_choice` legt het verschil vast.
        """
        if self.delta_pump_capacity_m3_per_sec <= 0:
            return 0.0
        return state.pump_capacity_m3_per_sec + self.delta_pump_capacity_m3_per_sec

    def apply(self, state: PolderState) -> PolderState:
        return state.replace(
            pump_capacity_m3_per_sec=(
                state.pump_capacity_m3_per_sec + self.delta_pump_capacity_m3_per_sec
            )
        )

    def upper_bound(self, state: PolderState) -> float:
        return state.pump_capacity_m3_per_sec * (MAX_PUMP_FACTOR - 1.0)


class VasthoudenAction(Action):
    """Vasthouden: de afvoer van een deel van het land wordt vertraagd.

    Verhoogt `retention_fraction`. Het aantal dagen vertraging is een ontwerpconstante van
    de polder en dus een eigenschap van de toestand, niet van de maatregel: anders is
    administratie per perceel nodig zodra er in twee stappen retentie wordt gebouwd met
    verschillende vertraging.
    """

    name_nl: ClassVar[str] = "vasthouden"
    name_en: ClassVar[str] = "retention"
    unit: ClassVar[str] = "ha land"

    delta_retention_ha: float = Field(0.0, ge=0.0)
    unit_cost: UnitCost | None = COST_RETENTION

    @property
    def magnitude(self) -> float:
        return self.delta_retention_ha

    def at(self, magnitude: float) -> "VasthoudenAction":
        return VasthoudenAction(delta_retention_ha=magnitude, unit_cost=self.unit_cost)

    def apply(self, state: PolderState) -> PolderState:
        added_fraction = self.delta_retention_ha / state.area_land_ha
        return state.replace(
            retention_fraction=min(state.retention_fraction + added_fraction, 1.0)
        )

    def upper_bound(self, state: PolderState) -> float:
        return state.area_land_ha * (1.0 - state.retention_fraction)
