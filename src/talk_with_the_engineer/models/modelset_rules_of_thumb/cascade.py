"""Een systeemvraag over meerdere gebieden, en wat er van terugkomt.

Het netwerk mag de toolgrens niet over. 8500 knopen passen niet in een toolaanroep, en als
ze passen zijn ze niet leesbaar; bovendien is een graaf als argument precies wat een LLM
slecht kan produceren en goed kan verzinnen. Zie PLAN_UITWISSELING_EN_NETWERK.md Sec. 8.

Wat er dus in gaat is een **selectie**, begrensd op `MAX_NODES`. En wat eruit komt is niet
het antwoord per knoop maar de bindende beperking en waar hij zit: dezelfde les als
`SolveStatus` en `LimitReason` uit WP5, nu op systeemschaal. Een agent kan niets met 8500
rijen en wel met "knoop C bindt, en daar levert bergen het meeste per euro".
"""

from pydantic import ConfigDict, Field, field_validator, model_serializer
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerOutputModel, StringTolerantInput
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    Assumption,
    ModelCaveat,
    RainfallInput,
    Sensitivity,
    hide_null_branch,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import round_floats

MAX_NODES = 50
"""Bovengrens op de selectie.

Niet de grens van de rekenkern - die doet 8500 knopen in 65 ms - maar van wat er zinvol
door een toolaanroep past en in een antwoord te lezen is. Wordt hij geraakt, dan is dat een
`ModelRetry` met de vraag om een kleiner gebied, en geen stille afkap.
"""


class CascadeNode(StringTolerantInput):
    """Eén gebied in de selectie, met de verbinding waarover het loost.

    Bewust geen `EngineerBaseModel`: dat draagt een `language`-veld, en dan adverteert elke
    knoop in de selectie een taal die alleen op de aanroep als geheel iets betekent. Een
    veld dat wordt geaccepteerd en genegeerd is erger dan geen veld - en op vijftig knopen
    is het ook nog vijftig keer schemaruis.
    """

    name: str = Field(
        ..., min_length=1, description="Naam van dit gebied; moet uniek zijn"
    )
    area_ha: float = Field(..., gt=0, description="Oppervlak van het gebied [ha]")
    percentage_open_water: float = Field(
        ..., gt=0, le=100, description="Percentage open water [%]"
    )
    discharge_capacity_m3_per_sec: float = Field(
        ..., ge=0, description="Gemaalcapaciteit van dit gebied [m3/s]"
    )
    drains_to: str | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Naam van het gebied waarop dit gebied loost. Laat weg als het op de "
            "buitenwereld loost - de zee, of een systeem buiten de selectie"
        ),
    )
    head_max_m: float | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Opvoerhoogte waarbij het gemaal tot stilstand komt [m]. Laat weg voor een "
            "peilonafhankelijk gemaal; dan is er geen terugkoppeling en is de doorrekening "
            "een enkele pass. Met een waarde erin duwt een volle benedenstroomse boezem "
            "terug op dit gemaal, en dat is waar de cascade over gaat"
        ),
    )
    retention_fraction: float | None = Field(
        None,
        ge=0,
        le=1,
        json_schema_extra=hide_null_branch,
        description="Fractie van het landoppervlak waarvan de afvoer wordt vertraagd",
    )
    # De peilband van dit gebied. Context en geen maatregel, net als op `WaterSystemInput`:
    # de losse tools konden een opgezette polder al doorrekenen, de cascade niet, en dan
    # stond elke knoop weer op [0, 0]. Zie PLAN_DROOGTE_EIS_ALS_WATERSTAND.md Sec. 4.4.
    target_level_rise_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilopzet van dit gebied: hoeveel het streefpeil al is verhoogd ten opzichte "
            "van het oorspronkelijke peil [m]. Telt mee in de gerapporteerde stijging, want "
            "die wordt boven het OORSPRONKELIJKE peil gemeten"
        ),
    )
    level_margin_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilmarge van dit gebied: hoe diep onder het streefpeil het gemaal mag "
            "doormalen [m]. Nul is het klassieke gedrag, waarbij het gemaal op streefpeil "
            "stopt"
        ),
    )


class CascadeInput(RainfallInput):
    """Wateroverlast op een cascade van gebieden die op elkaar lozen.

    De bui is de aanleiding; de vraag is waar de drainage vastloopt.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "return_period": 100,
                "nodes": [
                    {
                        "name": "polder A",
                        "area_ha": 4000,
                        "percentage_open_water": 3.5,
                        "discharge_capacity_m3_per_sec": 5,
                        "drains_to": "boezem",
                    },
                    {
                        "name": "boezem",
                        "area_ha": 8000,
                        "percentage_open_water": 3.5,
                        "discharge_capacity_m3_per_sec": 10,
                    },
                ],
            }
        }
    )

    nodes: list[CascadeNode] = Field(
        ...,
        min_length=1,
        max_length=MAX_NODES,
        description=(
            "De gebieden in de selectie, elk met het gebied waarop het loost. Houd het bij "
            "de gebieden die de vraag raken: dit antwoordt over een systeem en niet over "
            "een kaart"
        ),
    )

    @field_validator("nodes")
    @classmethod
    def names_are_unique(cls, nodes):
        """Weiger dubbele namen, met een melding in plaats van een validatiedump.

        Bewust een `ModelRetry` en geen `ValueError`. Pydantic vangt een `ValueError` uit
        een validator op en verpakt hem in een `ValidationError`, en die bereikt de beller
        als `[type=value_error, input_value=...]` met de hele knopenlijst en een link naar
        errors.pydantic.dev erbij - implementatiedetails die voor een beller ruis zijn.
        Een `ModelRetry` is geen `ValueError` en komt er dus onverpakt uit, net als de
        andere meldingen van deze toolset.
        """
        names = [node.name for node in nodes]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            listed = ", ".join(repr(name) for name in duplicates)
            raise ModelRetry(
                f"De namen van de gebieden moeten uniek zijn, en deze komt meer dan een "
                f"keer voor: {listed}. Hernoem het tweede gebied, of voeg de twee samen "
                f"als het er een is."
            )
        return nodes


class CascadeOutput(EngineerOutputModel):
    """Aggregaten en de bindende knoop; bewust niet een rij per gebied.

    Bij vijftig knopen is een rij per knoop nog leesbaar en bij duizend niet, en de vraag
    die iemand stelt is bijna nooit "geef me alle standen" maar "waar zit het probleem".
    Daarom staat hier het uiterste, de spreiding, en de knoop die bindt - en de volledige
    reeks per knoop niet.
    """

    description: str = Field(..., description="Twee uitlegbare zinnen over het systeem")
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description="Standaardwaarden waarmee gerekend is omdat ze niet zijn opgegeven",
    )
    sensitivity: list[Sensitivity] = Field(
        default_factory=list,
        description=(
            "Per aangenomen veld de hoogste stijging in de selectie aan de uiteinden van "
            "zijn plausibele bereik [m]. Ontbrak hier terwijl de acht maatregeltools hem "
            "wel hebben, en juist op een cascade waar vier waarden zijn aangenomen is de "
            "bandbreedte waardevol. Het gemelde antwoord is `worst_dh_m`, dus dat is wat er "
            "varieert"
        ),
    )
    caveats: list[ModelCaveat] = Field(
        default_factory=list,
        description=(
            "Structurele beperkingen die op dit antwoord van toepassing zijn. Op "
            "systeemschaal komt daar de koppelingswet bij: of een gemaal in werkelijkheid "
            "een pompkarakteristiek heeft of een uitschakelpeil is een open vraag, en de "
            "grootte van het cascade-effect hangt eraan"
        ),
    )
    node_count: int = Field(..., description="Aantal doorgerekende gebieden")
    depth: int = Field(
        ...,
        description=(
            "Aantal topologische lagen, en dus het aantal passes per iteratie. Voor een "
            "Nederlands watersysteem is dit 3 a 4 en niet het aantal gebieden"
        ),
    )
    converged: bool = Field(
        ...,
        description=(
            "Bij kopafhankelijke capaciteit wordt er geitereerd. Is dit false, dan zijn de "
            "standen optimistisch over de afvoer en dus ONVEILIG; gebruik ze niet als "
            "antwoord"
        ),
    )
    iterations: int = Field(..., description="Aantal iteraties tot convergentie")

    worst_node: str = Field(
        ..., description="Het gebied met de hoogste waterstandstijging"
    )
    worst_dh_m: float = Field(
        ..., description="De hoogste waterstandstijging in de selectie [m]"
    )
    median_dh_m: float = Field(
        ..., description="De mediane waterstandstijging over de selectie [m]"
    )
    lowest_dh_m: float = Field(
        ..., description="De laagste waterstandstijging in de selectie [m]"
    )

    binding_node: str | None = Field(
        None,
        description=(
            "Het gebied waarvan de benedenstroomse stand het meeste gemaalvermogen "
            "blokkeert, gemeten op het uur van zijn eigen piek. Dit is waar de koppeling "
            "knelt, en dus waar een maatregel het meeste doet. Null als er geen "
            "terugkoppeling in de selectie zit. Zijn er meer gebieden even hard "
            "geblokkeerd, dan staat hier de eerste uit de selectie en staan ze allemaal in "
            "`binding_nodes`"
        ),
    )
    binding_nodes: list[str] = Field(
        default_factory=list,
        description=(
            "Alle gebieden die even hard worden geblokkeerd als `binding_node`. Meestal "
            "een, en dan is dit `binding_node` in een lijst. Meer dan een betekent dat het "
            "model geen van de twee aanwijst: bij twee polders met dezelfde opvoerhoogte "
            "op dezelfde volle boezem staan beide gemalen volledig stil, en dan is er niets "
            "in dit model dat de een boven de ander kiest. Dat er stil een van de twee werd "
            "genoemd, maakte een willekeurige keuze onzichtbaar"
        ),
    )
    blocked_capacity_fraction: float | None = Field(
        None,
        description=(
            "Welk deel van het geinstalleerde gemaalvermogen van `binding_node` onbeschikbaar "
            "was op het uur van zijn eigen piek. Dit is het verschil tussen wat er is "
            "gekocht en wat er op het beslissende moment werkt"
        ),
    )
    coupling_effect_m: float | None = Field(
        None,
        description=(
            "Hoeveel hoger de piek van `worst_node` is dan wanneer elk gebied los zou "
            "worden gerekend [m]. Dit is de afwenteling, gemeten: zonder koppeling in het "
            "model is dit getal niet te zien en lijkt afvoeren goedkoper dan het is"
        ),
    )

    @model_serializer(mode="wrap")
    def _round_output(self, handler):
        """Rond de hele uitvoer af op significante cijfers; zie SIGNIFICANT_DIGITS.

        Stond hier niet, terwijl de maatregeltools en de aanvoertools hem wel hebben. Deze
        tool gaf dus `worst_dh_m: 4.315204656087141` waar de rest van het systeem 1,49 en
        68,18 meldt - vijftien decimalen bij een vuistregelmodel, en een beller kan die
        letterlijk doorgeven.
        """
        return round_floats(handler(self))
