"""De prijsvormen: wat een maatregel kost, en in welke vorm.

Dit is de kostenkant van `R`. Bewust los van `actions.py`: een prijs is een uitspraak over
geld en een actie een uitspraak over water, en de twee veranderen om verschillende redenen.
De maatregelcatalogus leunt hierop en niet andersom.

`UnitCost` is lineair per eenheid met een bandbreedte; `ValueCurve` is de geknikte vorm die
drooglegging nodig heeft. Wat hier nog niet staat is de TRAPKOST - een vast deel plus een
variabel deel - en die is nodig zodra sturing een maatregel wordt; zie issue #68 en
`PLAN_CORE_EPISTEMICS_INTERFACE.md` WP C1.

De eenheidskosten hieronder zijn onderbouwd met Nederlandse projecten en statistieken; elke
`UnitCost` draagt zijn eigen bron.
"""

from pydantic import BaseModel, ConfigDict, Field

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


class ValueCurve(BaseModel):
    """Grondwaarde als functie van drooglegging: een GEKNIKTE curve, geen prijs per cm.

    Dit staat hier omdat het de belangrijkste correctie is op hoe dit model peilopzet
    behandelde. `UnitCost` is een prijs per eenheid - lineair, met een band. Voor drooglegging
    is dat de verkeerde VORM, en dat is niet een kwestie van nauwkeurigheid maar van structuur.

    De gezaghebbende Nederlandse bron is de Compensatie Systematiek Veenweiden, vastgesteld
    door het dagelijks bestuur van Wetterskip Fryslan en gedeputeerde staten van Fryslan op
    4 juni 2024, extern gevalideerd door PPP Agro Advies en doorgerekend op BIN-cijfers van
    tien Friese veenweidebedrijven over 2019-2021. Die geeft drie eigenschappen die een
    constante niet kan reproduceren:

    * een **plateau** boven ongeveer 90 cm drooglegging - daar is de marginale prijs nul, want
      droger maakt de grond niet waardevoller;
    * een **klif** op 30 cm - daaronder vervalt "normaal agrarisch gebruik" en stort de waarde
      in. Dat is een discontinuiteit in de regelgeving, en hij is ook fysisch onderbouwd:
      onder 30 cm treedt fosfaatuitspoeling en pitrusgroei op;
    * **discrete stappen** van 1.500 euro per hectare per ruilklasse, want gelijke waardestappen
      zijn wettelijk verplicht. Een kleine peilopzet levert daardoor nul of een volle stap.

    Dat laatste is het scherpst te zien in het nagerekende voorbeeld uit het bijlagenboek: twee
    percelen met dezelfde 5 cm opzet, waarvan het ene 3.000 euro per hectare kost en het andere
    niets - alleen doordat het ene een klassegrens haalt en het andere niet.

    **Let op de herkomst.** Deze curve is voor veen en klei-op-veen in Fryslan. De VORM - een
    plateau, een klif, discrete stappen - is een eigenschap van de systematiek en van de
    fysica, en die verwacht je breder. De NIVEAUS zijn dat niet: de bovenwaarde van 53.000
    euro per hectare is een veenpolder, en landelijk grasland stond in 2025 op ongeveer 86.000.
    Gebruik deze curve dus niet buiten veengebied zonder dat op te schrijven.
    """

    model_config = ConfigDict(frozen=True)

    anchors: tuple[tuple[float, float], ...] = Field(
        ...,
        description=(
            "Ankerpunten (drooglegging in m, agrarische verkeerswaarde in EUR/ha), "
            "oplopend in drooglegging. Tussen de ankers lineair, erboven vlak"
        ),
    )
    price_level: str = Field(..., description="Prijspeil van de bedragen")
    applies_to: str = Field(
        ..., description="Waar deze curve voor geldt; buiten dat bereik niet gebruiken"
    )
    source: str = Field(..., description="Waar deze getallen vandaan komen")

    def value_at(self, drooglegging_m: float) -> float:
        """De agrarische verkeerswaarde bij deze drooglegging [EUR/ha]."""
        depths = [depth for depth, _value in self.anchors]
        values = [value for _depth, value in self.anchors]
        if drooglegging_m <= depths[0]:
            return values[0]
        if drooglegging_m >= depths[-1]:
            return values[-1]
        for (low, low_value), (high, high_value) in zip(self.anchors, self.anchors[1:]):
            if low <= drooglegging_m <= high:
                fraction = (drooglegging_m - low) / (high - low)
                return low_value + fraction * (high_value - low_value)
        raise AssertionError("onbereikbaar: de ankers dekken het hele bereik")

    def marginal_at(self, drooglegging_m: float) -> float:
        """Wat een METER minder drooglegging hier kost [EUR/ha per m].

        Nul op het plateau. Dat is geen afrondingsartefact maar de uitspraak: boven ongeveer
        90 cm koopt drogeren geen waarde meer, dus kost vernatten er ook geen.
        """
        for (low, low_value), (high, high_value) in zip(self.anchors, self.anchors[1:]):
            if low <= drooglegging_m <= high:
                return (high_value - low_value) / (high - low)
        return 0.0


DROOGLEGGING_VALUE_VEEN = ValueCurve(
    anchors=(
        (0.00, 5_000.0),
        (0.10, 13_000.0),
        (0.20, 22_000.0),
        (0.30, 28_000.0),
        (0.90, 53_000.0),
    ),
    price_level="eind 2021/2023",
    applies_to="veen en klei-op-veen, pilotgebied Aldeboarn-De Deelen Zuid (Fryslan)",
    source=(
        "Compensatie Systematiek Veenweiden, vastgesteld DB Wetterskip Fryslan en GS "
        "Fryslan 4 juni 2024; second opinion PPP Agro Advies; BIN-cijfers tien Friese "
        "veenweidebedrijven 2019-2021. De 30 cm is de bodemwaarde waaronder normaal "
        "agrarisch gebruik vervalt, de 90 cm de bovenwaarde"
    ),
)
"""De enige vastgestelde Nederlandse curve die we hebben gevonden; zie `ValueCurve`.

Individueel toegekende nadeelcompensatie wordt niet als bedrag gepubliceerd - dat zijn
beschikkingen aan een benoemde partij - dus dit is geen steekproef uit de praktijk maar de
METHODIEK waarmee die bedragen worden bepaald. Dat is voor een vuistregel het betere anker.
"""

CAPITALISATION_FACTOR = 10
"""Van jaarschade naar eenmalig bedrag; standaard bij nadeelcompensatie voor eigenaar-gebruikers.

Staat als "deze factor is standaard" in de CSV en is vaste jurisprudentie. Bij pacht lager.

Let op de valkuil die de CSV zelf blootlegt: tel GEEN gekapitaliseerde inkomensschade boven op
de waardedaling. In het uitgewerkte voorbeeld is de inkomensschade zelfs NEGATIEF - een
inkomensvoordeel - omdat de eenmalige vermogenscompensatie de verloren productiecapaciteit al
kapitaliseert. Beide optellen is dubbeltellen.
"""


def peilopzet_unit_cost(
    area_ha: float,
    drooglegging_m: float,
    curve: ValueCurve = DROOGLEGGING_VALUE_VEEN,
) -> UnitCost:
    """Bouw de prijs van peilopzet uit de curve, voor DEZE polder op DIT punt.

    Hiermee kan een beller peilopzet correct prijzen in plaats van dat het model een prijs
    verzint of hem op nul zet. De teruggegeven `UnitCost` is een lokale linearisatie: hij geldt
    in de band waarin `drooglegging_m` valt en nergens anders, want de curve knikt.

    De band als bandbreedte: de marginale prijs loopt over de curve van nul (plateau) tot
    900 euro per hectare per centimeter (onder 20 cm). Dat is geen onzekerheid over de prijs
    maar spreiding over de POLDER, en daarom is het eerlijker om hem als band te melden dan om
    het middelpunt te nemen.
    """
    marginal = curve.marginal_at(drooglegging_m)
    steepest = max(
        curve.marginal_at(0.5 * (low + high))
        for (low, _lv), (high, _hv) in zip(curve.anchors, curve.anchors[1:])
    )
    return UnitCost(
        typical=max(marginal * area_ha, 1.0),
        low=max(marginal * area_ha, 1.0),
        high=max(steepest * area_ha, 1.0),
        unit="EUR per m peilopzet over het hele gebied",
        price_level=curve.price_level,
        source=(
            f"{curve.source}; gelineariseerd bij een drooglegging van "
            f"{drooglegging_m * 100:.0f} cm over {area_ha:g} ha. Geldt voor: "
            f"{curve.applies_to}"
        ),
    )
