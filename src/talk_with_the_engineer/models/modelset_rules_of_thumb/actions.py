"""Maatregelen als getypeerde acties op de polder-toestand.

Dit is het `a` uit `s' = f(s, a, w)`. Elke maatregel raakt precies een toestandsveld, en
draagt zijn eigen eenheid en prijs. De eenheden zijn niet uitwisselbaar: bij bergen wordt
land gekocht, bij vasthouden het recht om het af en toe onder water te zetten.

De eenheidskosten hieronder zijn onderbouwd met Nederlandse projecten en statistieken;
elke `UnitCost` draagt zijn eigen bron, en `sources` zegt wat er buiten die getallen valt.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState

# Afvoeren heeft geen harde fysieke bovengrens. Dit plafond bestaat zodat een onhaalbaar
# doel in een eindige zoekruimte blijft en als `physical_upper_bound` gemeld wordt.
MAX_PUMP_FACTOR = 20.0

# Zoekgrens voor de peilmarge, geen fysieke constante: dieper dan een meter onder
# streefpeil is geen peilbeheer meer maar droogvallen. Wordt als
# `physical_upper_bound` gemeld als hij geraakt wordt.
MAX_LEVEL_MARGIN_M = 1.0

# Zoekgrens voor de inlaatcapaciteit in l/s/ha over het hele gebied. De aanvoernorm
# is 0,3 tot 0,4 l/s/ha; dit is ruim een orde daarboven, zodat de bisectie ook een
# extreem tekort kan dekken en de grens nooit stil bindend is.
MAX_SUPPLY_L_S_HA = 5.0

# Zoekgrens voor de peilopzet. Geen fysieke grens: wat een polder werkelijk aan opzet
# verdraagt is de drooglegging, en die wordt door de inundatie-eis afgedwongen.
MAX_TARGET_LEVEL_RISE_M = 1.0

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


SHARE_EPSILON = 1e-9
"""Onder deze verschuiving in procentpunten is er afrondingsruis en geen maatregel."""


class Action(BaseModel, ABC):
    """Een maatregel met maatvoering."""

    model_config = ConfigDict(frozen=True)

    name_nl: ClassVar[str]
    name_en: ClassVar[str]
    unit: ClassVar[str]

    plateau_kind: ClassVar[str] = "plateau"
    """Wat een vlakke respons betekent bij deze maatregel: `plateau` of `saturated`.

    Of een vlak stuk "hier is niets meer te halen" betekent of "een andere grootheid is
    de klem" is een modelfeit over de maatregel en niet iets wat uit de curve te lezen is.
    Daarom staat het hier en niet in een heuristiek in `classify_optimum`. De waarden zijn
    die van `OptimumKind`; als string om een importcyclus met `results` te vermijden.
    """

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
    def current_magnitude(self, state: PolderState) -> float:
        """De huidige waarde van de grootheid die DEZE maatregel vergroot, in `unit`.

        Hiermee wordt `MeasureChange` opgebouwd: `current_magnitude(state)` is de
        beginwaarde, en `+ magnitude` is waar je uitkomt. De invariant is dus

            current_magnitude(state) + magnitude == current_magnitude(apply(state))

        en `test_the_measure_change_adds_up` legt die voor alle maatregelen vast.

        Waarom hier en niet als een diff van twee toestanden: alleen de maatregel zelf weet
        wélke grootheid hij verandert en in welke eenheid hij hem uitdrukt. Vasthouden werkt
        op `retention_fraction` maar rapporteert hectares land; bergen werkt op
        `pct_open_water` maar rapporteert hectares open water. Een diff op de toestand zou
        dat moeten raden.

        Vaak nul, en dat is geen ontbrekende invoer: een polder heeft standaard geen
        retentie en geen inlaat.
        """
        raise NotImplementedError

    share_of_nl: ClassVar[str | None] = None
    """Waarvan `area_share` een percentage is, in woorden. `None` als het geen aandeel is.

    Bergen en vasthouden werken allebei op een aandeel, maar op een ANDER aandeel, en dat
    verschil is geen detail: open water is een deel van het hele gebied, vertraagd land is
    een deel van het landoppervlak. Op dat open water kun je niets vasthouden.

    Eerder werd vasthouden hier omgerekend naar een percentage van het hele gebied, "voor
    consistentie met bergen". Dat leverde een grootheid op die niemand gebruikt - "57 % van
    mijn polder inclusief het water is retentiegebied" - en het kocht geen vergelijkbaarheid,
    want de twee maatregelen doen niet hetzelfde. De regel is nu: elke maatregel rapporteert
    zijn EIGEN aandeel-variabele, en zegt erbij waarvan.
    """

    def area_share(self, state: PolderState) -> float | None:
        """Het aandeel dat deze maatregel verschuift [%], of `None`.

        De noemer verschilt per maatregel en staat in `share_of_nl`. Bergen rapporteert
        `pct_open_water` - een deel van het gebied - en vasthouden `retention_fraction`, een
        deel van het land. Allebei zijn het variabelen die het model zelf bijhoudt, dus er
        wordt niets omgerekend.

        Een gemaal en een inlaat zijn een capaciteit en geen aandeel; daar is een
        procentpunt betekenisloos en is dit `None`.

        Dit staat op de maatregel en niet als een diff van twee toestanden, om dezelfde
        reden als `current_magnitude`: als een maatregel niets verandert, is uit de
        toestanden niet meer af te leiden welke grootheid hij zou hebben veranderd. Dan gaf
        een diff `0,0` voor afvoeren, alsof gemaalcapaciteit een aandeel is.
        """
        return None

    def area_share_delta(self, state: PolderState) -> float | None:
        """De verschuiving van dat aandeel in PROCENTPUNTEN, of `None`.

        Nul blijft nul. Zonder de drempel meldde een maatregel die niets doet
        `4,4e-16 procentpunt`: `pct_open_water` wordt via het areaal heen en weer gerekend
        en komt dan een ULP naast zijn eigen beginwaarde uit. Dat getal ging als getal de
        uitvoer in.
        """
        before = self.area_share(state)
        if before is None:
            return None
        shift = self.area_share(self.apply(state)) - before
        return 0.0 if abs(shift) < SHARE_EPSILON else shift

    def upper_bound(self, state: PolderState) -> float:
        """De grootste maatvoering die in deze toestand mogelijk is."""

    def chargeable_quantity(self, state: PolderState) -> float:
        """Waarover de eenheidsprijs gerekend wordt.

        Standaard de maatvoering zelf: bergen en vasthouden zijn lineair in het areaal.
        Afvoeren wijkt af, zie `AfvoerenAction`.
        """
        return self.magnitude

    def cost(self, state: PolderState) -> float | None:
        """Investeringskosten [EUR]; geen exploitatie, geen energie, geen onderhoud."""
        if self.unit_cost is None:
            return None
        return self.unit_cost.typical * self.chargeable_quantity(state)

    def cost_range(self, state: PolderState) -> tuple[float, float] | None:
        """Onder- en bovengrens van de investeringskosten [EUR]."""
        if self.unit_cost is None:
            return None
        quantity = self.chargeable_quantity(state)
        return self.unit_cost.low * quantity, self.unit_cost.high * quantity

    def replacement_quantity(self, state: PolderState) -> float:
        """Waarover de prijs gerekend wordt in de TRAPKOST-lezing.

        Standaard hetzelfde als `chargeable_quantity`: bergen en vasthouden zijn werkelijk
        lineair in het areaal - je koopt hectares, en tien hectare kost tien keer een
        hectare. Afvoeren wijkt af en overschrijft dit: je koopt een gemaal en niet een
        m3/min, dus de prijs hangt aan de nieuwe TOTALE capaciteit en niet aan de toename.

        Bestaat als eigen hook zodat de twee lezingen naast elkaar te melden zijn in plaats
        van dat er een gekozen moet worden. Zie `replacement_cost`.
        """
        return self.chargeable_quantity(state)

    def replacement_cost(self, state: PolderState) -> float | None:
        """De prijs in de trapkost-lezing [EUR].

        **Dit is niet een correctie op `cost` maar een tweede lezing ernaast.** Lineair
        rekenen is een bewuste vuistregelvereenvoudiging met een bekende richting: het
        onderschat een kleine uitbreiding sterk. Op de referentiepolder is 2,91 m3/s extra
        lineair 5,59 mln en als vervanging 15,19 mln - een factor 2,7.

        En dat verschil is niet cosmetisch, want het verandert de RANGORDE. In de lineaire
        lezing kost bergen 111 ha 15,01 mln en is afvoeren met +169 % onbereikbaar ver weg;
        in de trapkost-lezing liggen die twee 1,2 % uit elkaar met overlappende prijsbanden,
        en dan zijn ze niet van elkaar te onderscheiden. Dát is het plateau uit issue #30, en
        het is onzichtbaar zolang er maar een lezing wordt gemeld.
        """
        if self.unit_cost is None:
            return None
        return self.unit_cost.typical * self.replacement_quantity(state)

    def replacement_cost_range(self, state: PolderState) -> tuple[float, float] | None:
        """Onder- en bovengrens van de trapkost-lezing [EUR]; zie `replacement_cost`."""
        if self.unit_cost is None:
            return None
        quantity = self.replacement_quantity(state)
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

    def current_magnitude(self, state: PolderState) -> float:
        """Het open water dat er nu ligt [ha]; bergen maakt daar land bij open water."""
        return state.area_open_water_ha

    share_of_nl: ClassVar[str] = "het gebied"

    def area_share(self, state: PolderState) -> float | None:
        """Open water is een aandeel van het hele gebied; dat is `pct_open_water`."""
        return state.pct_open_water

    def upper_bound(self, state: PolderState) -> float:
        # al het resterende land kan in principe open water worden
        return max(state.area_ha - state.area_open_water_ha, 0.0)


class WaterExchangeAction(Action, ABC):
    """Uitwisseling over de systeemgrens: meer capaciteit in een van beide richtingen.

    Afvoeren en aanvoeren zijn niet twee acties maar een transitie met twee richtingen -
    water verplaatsen over de systeemgrens. Deze klasse is die transitie; de richting staat
    als `direction` op de subklasse.

    Waarom de richting op de actie staat en niet als teken op de capaciteit: een gemaal en
    een inlaat zijn twee kunstwerken met twee prijzen die beide kunnen bestaan, dus de
    *toestand* heeft twee niet-negatieve capaciteiten. De *actie* zegt welke van de twee
    hij vergroot. Signed actie, ongesigneerde toestand. Zie `Connection`.

    Wat de subklassen wel eigen houden zijn hun veldnaam, hun eenheid, hun prijs en hun
    teksten. Dat is geen duplicatie van de transitie maar het verschil dat er werkelijk is:
    de bui, het doel, de kostenstructuur en de randvoorwaarde zijn voor nat en droog vier
    verschillende dingen.
    """

    direction: ClassVar[Literal["out", "in"]]

    @property
    def direction_label(self) -> str:
        """Hoe de richting in de uitvoer heet."""
        return "outflow" if self.direction == "out" else "inflow"

    def current_capacity(self, state: PolderState) -> float:
        """De capaciteit die deze actie vergroot [m3/s]."""
        if self.direction == "out":
            return state.pump_capacity_m3_per_sec
        return state.supply_capacity_m3_per_sec

    def apply(self, state: PolderState) -> PolderState:
        new_capacity = self.current_capacity(state) + self.magnitude
        if self.direction == "out":
            return state.with_capacity(capacity_out_m3_per_sec=new_capacity)
        return state.with_capacity(capacity_in_m3_per_sec=new_capacity)


class AfvoerenAction(WaterExchangeAction):
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
    aanname en niet uit de hydrologie.

    `replacement_quantity` geeft de trapkost-lezing, zodat de afwijking na te rekenen is.
    """

    name_nl: ClassVar[str] = "afvoeren"
    name_en: ClassVar[str] = "discharge"
    unit: ClassVar[str] = "m3/s"
    direction: ClassVar[Literal["out", "in"]] = "out"

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

        Dit is de enige actie die de basisimplementatie overschrijft, en dat is precies waar
        het over gaat: bergen en vasthouden zijn werkelijk lineair - je koopt hectares - en
        een gemaal is dat niet.
        """
        if self.delta_pump_capacity_m3_per_sec <= 0:
            return 0.0
        return state.pump_capacity_m3_per_sec + self.delta_pump_capacity_m3_per_sec

    def current_magnitude(self, state: PolderState) -> float:
        """De gemaalcapaciteit die er nu staat [m3/s]."""
        return state.pump_capacity_m3_per_sec

    def upper_bound(self, state: PolderState) -> float:
        return state.pump_capacity_m3_per_sec * (MAX_PUMP_FACTOR - 1.0)


class PeilmargeAction(Action):
    """Voorbemaling: het gemaal mag verder doormalen dan het streefpeil.

    Verhoogt `level_margin_m`. Wat voorbemalen werkelijk kost is tweeledig: de sturing die
    hem mogelijk maakt (telemetrie, automatisering, protocollen - een investering met een
    vaste kostenvorm: je koopt een systeem, geen centimeters) en in de bedrijfsvoering
    voorraad en drooglegging, een verdringingsvraag. `unit_cost=None` omdat geen van beide
    in een lineaire prijs per meter past; een verzonnen lineaire prijs is hier erger dan
    geen prijs.

    De maatregel **verzadigt**, en dat is het interessante ervan. Op de referentiebui
    levert 10 cm marge 10,0 cm lagere piek en levert 30 cm marge nog steeds 10,5 cm: het
    gemaal maalt 0,31 m per dag leeg en de droge uren voor de piek zijn op. Meer marge
    afspreken levert dan niets meer op, en `OptimumKind.SATURATED` zegt dat.

    Dit is niet peilopzet met een ander teken; zie de docstring van `PolderState`.
    """

    name_nl: ClassVar[str] = "voorbemalen"
    name_en: ClassVar[str] = "prerelease"
    unit: ClassVar[str] = "m peilmarge"
    plateau_kind: ClassVar[str] = "saturated"

    delta_level_margin_m: float = Field(0.0, ge=0.0)
    unit_cost: UnitCost | None = None

    @property
    def magnitude(self) -> float:
        return self.delta_level_margin_m

    def at(self, magnitude: float) -> "PeilmargeAction":
        return PeilmargeAction(delta_level_margin_m=magnitude, unit_cost=self.unit_cost)

    def apply(self, state: PolderState) -> PolderState:
        return state.replace(
            level_margin_m=state.level_margin_m + self.delta_level_margin_m
        )

    def current_magnitude(self, state: PolderState) -> float:
        """De peilmarge die nu is afgesproken [m]."""
        return state.level_margin_m

    def upper_bound(self, state: PolderState) -> float:
        # De bruikbare slootdiepte onder streefpeil. Geen fysieke constante maar een
        # zoekgrens: dieper dan dit is geen peilbeheer meer maar droogvallen.
        return max(MAX_LEVEL_MARGIN_M - state.level_margin_m, 0.0)


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

    def current_magnitude(self, state: PolderState) -> float:
        """Het land waarvan de afvoer nu al wordt vertraagd [ha].

        Een fractie van het LANDoppervlak en niet van het hele gebied; dat is dezelfde
        conversie die `apply` gebruikt, andersom.
        """
        return state.retention_fraction * state.area_land_ha

    share_of_nl: ClassVar[str] = "het landoppervlak"

    def area_share(self, state: PolderState) -> float | None:
        """Vertraagd land is een aandeel van het LAND; dat is `retention_fraction`.

        Niet omgerekend naar het hele gebied: op het open water kun je niets vasthouden, dus
        die noemer zou een grootheid opleveren die niemand gebruikt.
        """
        return state.retention_fraction * 100.0

    def upper_bound(self, state: PolderState) -> float:
        return state.area_land_ha * (1.0 - state.retention_fraction)


# Er hangt bewust geen prijs aan aanvoeren. Wat aanvoer kost is in een tekort niet de
# inlaat maar het water, en dat is een verdelingsvraag: de verdringingsreeks rantsoeneert
# landelijk, en de aanvoercapaciteit van een verziltende polder wordt bovendien
# gedimensioneerd op doorspoeling en dus op waterkwaliteit in plaats van kwantiteit -
# doorspoelen haalt 3 tot 5 % efficientie. Een verzonnen getal zou hier erger zijn dan
# geen getal.
#
# Net als bij peilopzet geldt: geen prijs is niet gratis. Komt aanvoeren ooit in een
# pakketzoeker terecht, dan hoort hij daar via `Package.priceless` en `switch_price_of`
# in plaats van via een stille nul.
class AanvoerenAction(WaterExchangeAction):
    """Aanvoeren: meer inlaatcapaciteit. Verhoogt `capacity_in_m3_per_sec`.

    Dezelfde transitie als afvoeren, tegengestelde richting. Wat wel anders is: de
    aandrijving is een neerslagtekort van weken in plaats van een bui van dagen, de
    ordegrootte is een factor tien kleiner - de aanvoernorm is 0,3 tot 0,4 l/s/ha tegen
    1 tot 5 voor een gemaal - en het kunstwerk is een inlaat die op zwaartekracht loopt.
    Daarom een eigen actie met een eigen naam boven op de gedeelde transitie.
    """

    name_nl: ClassVar[str] = "aanvoeren"
    name_en: ClassVar[str] = "supply"
    unit: ClassVar[str] = "m3/s inlaat"
    direction: ClassVar[Literal["out", "in"]] = "in"

    delta_supply_capacity_m3_per_sec: float = Field(0.0, ge=0.0)
    unit_cost: UnitCost | None = None

    @property
    def magnitude(self) -> float:
        return self.delta_supply_capacity_m3_per_sec

    def at(self, magnitude: float) -> "AanvoerenAction":
        return AanvoerenAction(
            delta_supply_capacity_m3_per_sec=magnitude, unit_cost=self.unit_cost
        )

    def current_magnitude(self, state: PolderState) -> float:
        """De inlaatcapaciteit die er nu staat [m3/s]; standaard nul."""
        return state.supply_capacity_m3_per_sec

    def upper_bound(self, state: PolderState) -> float:
        """Zoekgrens: de vraag die het hele gebied bij het maximale tekort kan hebben.

        Geen fysieke grens maar een zoekgrens, en ruim genomen. Meer inlaatcapaciteit dan
        de vraag is per definitie zinloos, dus hoger hoeft de bisectie niet te kijken.
        """
        return MAX_SUPPLY_L_S_HA * state.area_ha / 1000.0


class PeilopzetAction(Action):
    """Peilopzet: het streefpeil gaat omhoog. Verhoogt `target_level_rise_m`.

    Dit is de enige maatregel die voorraad *koopt*: de berging onder het streefpeil is het
    enige water dat het gemaal niet wegpompt. Bergen maakt elke centimeter opzet
    productiever - de voorraad schaalt met het open wateroppervlak - maar zonder opzet is
    er geen voorraad om te schalen.

    **Er hangt geen prijs aan, en dat is geen omissie.** Peilopzet kost geen aanleg maar
    drooglegging, en dus landbouwschade en functiebeperking; dat is een verdringingsvraagstuk
    en geen investeringspost. Maar hij is in dit model ook niet gratis: `target_level_rise_m`
    telt op in `dh_total_above_original_datum_m`, dus elke centimeter opzet is een centimeter
    minder marge tot de inundatienorm. De kosten worden dus door de inundatie-eis afgedwongen
    en niet door een euro. Dat is de spanning waar dit model op rust: de natte en de droge
    eis delen een schaarse grootheid.

    **"Geen prijs" is niet "gratis", en het verschil bepaalt de uitkomst.** Zolang de
    pakketzoeker `None` als nul behandelde, kocht peilopzet inundatiemarge zonder tegenprijs
    en verschoof het goedkoopste pakket van bergen naar afvoeren. De ontbrekende prijs zat
    dus niet in de rapportage maar in het ANTWOORD. `Package.priceless` meldt hem nu, en
    `switch_price_of` leest af welke prijs hij zou moeten hebben voordat het antwoord
    verandert - op de referentiepolder ongeveer 0,14 miljoen euro per centimeter voordat
    bergen erbij komt, en 1,5 miljoen voordat afvoeren verdwijnt. Dat getal komt uit het
    model; een verzonnen prijs zou dat niet doen. Zie issue #30.

    Niet te verwarren met `PeilmargeAction`. Dat is de onderkant van dezelfde band en die
    verzadigt; deze is lineair en onbegrensd. Zie de docstring van `PolderState`.
    """

    name_nl: ClassVar[str] = "peilopzet"
    name_en: ClassVar[str] = "raise target level"
    unit: ClassVar[str] = "m peilopzet"

    delta_target_level_rise_m: float = Field(0.0, ge=0.0)
    unit_cost: UnitCost | None = None

    @property
    def magnitude(self) -> float:
        return self.delta_target_level_rise_m

    def at(self, magnitude: float) -> "PeilopzetAction":
        return PeilopzetAction(
            delta_target_level_rise_m=magnitude, unit_cost=self.unit_cost
        )

    def apply(self, state: PolderState) -> PolderState:
        return state.replace(
            target_level_rise_m=state.target_level_rise_m
            + self.delta_target_level_rise_m
        )

    def current_magnitude(self, state: PolderState) -> float:
        """De peilopzet die nu al is toegepast [m]."""
        return state.target_level_rise_m

    def upper_bound(self, state: PolderState) -> float:
        """Zoekgrens. Wat werkelijk bindt is de inundatie-eis, niet dit getal."""
        return max(MAX_TARGET_LEVEL_RISE_M - state.target_level_rise_m, 0.0)
