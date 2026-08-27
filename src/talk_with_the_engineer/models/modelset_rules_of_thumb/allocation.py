"""Een verdelingsvraag over meerdere gebieden die één bron delen, en wat er van terugkomt.

De droge tegenhanger van `region.py`, en dezelfde toolgrens-discipline: de graaf komt er niet
over. Wat er in gaat is een **selectie**, begrensd op `MAX_NODES`; wat eruit komt is niet een
rij per afnemer maar de bindende categorie en de trap. Een agent kan niets met achthonderd
volumes en wel met "vanaf 40 % aanbod krijgt landbouw niets".

**Waarom dit een eigen tool is en geen vlag op de aanvoertool.** De bestaande aanvoertools
rekenen één gebied door en nemen daarbij aan dat het water bij de inlaat is. Dat is geen fout
antwoord op de vraag die gesteld is, maar het is een andere vraag: bij één afnemer is er
niets te verdringen. Verdringing heeft concurrenten nodig, en dus een selectie.
"""

from typing import Literal

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerOutputModel, StringTolerantInput
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    Assumption,
    ModelCaveat,
    hide_null_branch,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.drought import (
    SourceVolumeInput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import round_floats

MAX_NODES = 50
"""Bovengrens op de selectie; zelfde reden als bij `CascadeInput`.

Niet de grens van de rekenkern - die doet 8500 afnemers in 22 ms - maar van wat er zinvol
door een toolaanroep past en in een antwoord te lezen is.
"""

CATEGORIES = (1, 2, 3, 4)
"""De vier categorieën van de wettelijke verdringingsreeks, artikel 3.14 Bkl.

1. veiligheid en het voorkomen van onomkeerbare schade
2. nutsvoorzieningen (drinkwater, energie), voor zover het de leveringszekerheid raakt
3. kleinschalig hoogwaardig gebruik: beregening van kapitaalintensieve gewassen, proceswater
4. overige belangen, af te wegen op economische en maatschappelijke schade - scheepvaart,
   landbouw, natuur, industrie, recreatie

Binnen 1 en 2 is er een prioriteitsvolgorde; binnen 3 en 4 gebeurt prioritering op basis van
minimalisatie van de economische maatschappelijke schade. En tussen 3 en 4 is nadere
prioritering **niet mogelijk** - de schillen zijn ondoordringbaar.
"""


class AllocationNode(StringTolerantInput):
    """Eén afnemer in de selectie, met de bron waaruit hij trekt.

    Bewust geen `EngineerBaseModel`: dat draagt een `language`-veld, en dan adverteert elke
    afnemer een taal die alleen op de aanroep als geheel iets betekent. Zie `CascadeNode`.
    """

    name: str = Field(
        ..., min_length=1, description="Naam van dit gebied; moet uniek zijn"
    )
    area_ha: float = Field(..., gt=0, description="Oppervlak van het gebied [ha]")
    deficit_mm_per_day: float = Field(
        ...,
        ge=0,
        description=(
            "Het neerslagtekort van dit gebied [mm/dag]. Maal het oppervlak en de duur "
            "geeft de watervraag; die vraag is wat er verdeeld wordt"
        ),
    )
    category: Literal[CATEGORIES] = Field(
        ...,
        description=(
            "Categorie uit de wettelijke verdringingsreeks (art. 3.14 Bkl): 1 = veiligheid "
            "en onomkeerbare schade, 2 = nutsvoorzieningen, 3 = kleinschalig hoogwaardig "
            "gebruik, 4 = overige belangen waaronder landbouw. Lagere categorieen krijgen "
            "pas water als de hogere gedekt zijn, en daar kan geen weging tegenop"
        ),
    )
    intake_capacity_m3_per_sec: float = Field(
        ...,
        ge=0,
        description=(
            "Inlaatcapaciteit van dit gebied [m3/s]. Dit is een GRENS en geen toewijzing: "
            "meer water in de boezem verandert niets aan wat er door deze inlaat past"
        ),
    )
    draws_from: str | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Naam van het gebied waaruit dit gebied inlaat - doorgaans de boezem. Laat weg "
            "als het rechtstreeks uit de bron trekt. Dit is dezelfde verbinding als "
            "`drains_to` op de natte kant, andersom gelezen: een gemaal en een inlaat "
            "hangen aan dezelfde kant"
        ),
    )


class AllocationInput(SourceVolumeInput):
    """Watertekort over een selectie van gebieden die één bron delen.

    De droogte is de aanleiding; de vraag is wie er water krijgt en wie tekortkomt.

    Het bronvolume is hier het onderwerp en niet een randvoorwaarde, en het erft daarom
    dezelfde tweetakt als bij aanvoeren: zelf opgeven, of laten afleiden uit de
    droogtestatistiek met `source_volume_normal_year_m3`, `source_river` en het tripel. Dat
    tweede is hier het meest waard - de vraag "vanaf welk aanbod valt landbouw af" is pas een
    beleidsvraag zodra dat aanbod bij een herhaaltijd hoort in plaats van bij een aanname.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "available_source_volume_m3": 4000000,
                "nodes": [
                    {
                        "name": "drinkwaterinname",
                        "area_ha": 500,
                        "deficit_mm_per_day": 4,
                        "category": 2,
                        "intake_capacity_m3_per_sec": 1.0,
                        "draws_from": "boezem",
                    },
                    {
                        "name": "landbouwpolder",
                        "area_ha": 4000,
                        "deficit_mm_per_day": 4,
                        "category": 4,
                        "intake_capacity_m3_per_sec": 1.5,
                        "draws_from": "boezem",
                    },
                    {
                        "name": "boezem",
                        "area_ha": 8000,
                        "deficit_mm_per_day": 0,
                        "category": 4,
                        "intake_capacity_m3_per_sec": 10.0,
                    },
                ],
            }
        }
    )

    language: Literal["nl", "en"] = Field(
        "nl", description="Taal van de uitlegzin in de uitvoer"
    )
    length_days: int | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Duur van de droogteperiode in dagen. Maal het tekort geeft de vraag, en de "
            "inlaatcapaciteiten worden hierover in volumes omgerekend. Weet je dit niet, "
            "laat het veld dan weg in plaats van het te schatten; de tool rekent met 30 "
            "dagen en meldt dat in `assumptions`"
        ),
    )
    nodes: list[AllocationNode] = Field(
        ...,
        min_length=1,
        max_length=MAX_NODES,
        description=(
            "De gebieden in de selectie, elk met zijn categorie en de bron waaruit het "
            "trekt. Houd het bij de gebieden die om hetzelfde water concurreren: dit "
            "antwoordt over een verdeling en niet over een kaart"
        ),
    )

    @model_validator(mode="after")
    def fill_allocation_defaults(self):
        self._apply_fallbacks("length_days")
        return self

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


# Een uitvoermodel en bewust geen `EngineerBaseModel`: dat draagt een `language`-veld dat
# bij een toolaanroep hoort, en dan krijgt elk object in `theta_steps` een `"language":
# "nl"` mee - een invoerveld in een resultaat. De docstring hieronder komt in het
# uitvoerschema terecht en houdt dat soort intern nieuws er dus buiten.
class ThetaStep(EngineerOutputModel):
    """Eén trede van de droogtetrap: een bereik van aanbod met één regime erin.

    Binnen een trede is de toewijzing lineair in het aanbod: er verandert niets aan welke
    klem bindt, alleen aan hoeveel er doorheen gaat. De dekking loopt daarom van
    `coverage_at_low` naar `coverage_at_high`, en het antwoord bij een aanbod ergens in de
    trede ligt tussen die twee in.
    """

    theta_low: float = Field(
        ..., description="Ondergrens van dit stuk, als fractie van de totale vraag"
    )
    theta_high: float = Field(..., description="Bovengrens van dit stuk")
    coverage_at_low: dict[str, float] = Field(
        ...,
        description=(
            "Dekkingsfractie per categorie bij `theta_low`, de ONDERkant van dit stuk. De "
            "sleutel is de categorie als tekst, omdat JSON-objecten geen getallen als "
            "sleutel hebben. Binnen het stuk loopt de dekking lineair van hier naar "
            "`coverage_at_high`, dus dit paar is het bereik en geen van beide is 'de' "
            "dekking van het stuk"
        ),
    )
    coverage_at_high: dict[str, float] = Field(
        ...,
        description=(
            "Dekkingsfractie per categorie bij `theta_high`, de BOVENkant van dit stuk. "
            "De sleutel is de categorie als tekst. Dit is NIET de dekking binnen het stuk: "
            "samen met `coverage_at_low` vormt hij de twee einden van een bereik, en het "
            "antwoord bij een aanbod ergens in het stuk ligt daartussen"
        ),
    )
    binding_category: int | None = Field(
        None,
        description="De laagste categorie die hier niet volledig gedekt is; null als alles rond is",
    )
    binding_is_capacity_not_availability: bool = Field(
        ...,
        description=(
            "True als het tekort op dit stuk door de INLATEN komt en niet door de bron. "
            "Twee aangrenzende stappen kunnen dezelfde dekking en dezelfde bindende "
            "categorie hebben en toch iets anders betekenen: op de ene is er te weinig "
            "water, op de andere past het er niet doorheen. Dat is het verschil tussen een "
            "rantsoeneringsvraag en een kunstwerkvraag"
        ),
    )
    contains_current_theta: bool = Field(
        False,
        description=(
            "True op de trede waarin het opgegeven aanbod valt, en op alle andere false; "
            "bij een onbeperkte bron overal false. Gebruik hem om de trede te vinden zonder "
            "zelf te matchen. Op die trede ligt `coverage_per_category` ergens TUSSEN "
            "`coverage_at_low` en `coverage_at_high`, en dus op geen van beide"
        ),
    )


class AllocationOutput(EngineerOutputModel):
    """Wie er afvalt en vanaf wanneer; bewust niet een rij per afnemer.

    Dezelfde keuze als `CascadeOutput`. De vraag die iemand stelt is bijna nooit "geef me alle
    volumes" maar "wie krijgt niets, en hoe droog moet het daarvoor zijn".
    """

    description: str = Field(
        ..., description="Twee uitlegbare zinnen over de verdeling"
    )
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description="Standaardwaarden waarmee gerekend is omdat ze niet zijn opgegeven",
    )
    caveats: list[ModelCaveat] = Field(
        default_factory=list,
        description=(
            "Structurele beperkingen die op dit antwoord van toepassing zijn. Op een "
            "verdelingsvraag komt daar de regel binnen een categorie bij: de wet noemt "
            "schademinimalisatie, en dit model verdeelt bij gebrek aan schadefuncties gelijk"
        ),
    )

    node_count: int = Field(..., description="Aantal afnemers in de selectie")
    depth: int = Field(
        ...,
        description=(
            "Aantal topologische lagen. Voor een Nederlandse selectie is dit 2 a 3 - "
            "peilvak, boezem, bron - en niet het aantal gebieden"
        ),
    )
    within_shell_rule: str = Field(
        ...,
        description=(
            "Hoe er binnen een categorie is verdeeld. `proportional` is gelijk tekort, en "
            "dat is een PROXY voor het wettelijke criterium van schademinimalisatie"
        ),
    )

    available_source_volume_m3: float | None = Field(
        None,
        description=(
            "Het bronvolume waarmee verdeeld is [m3]; null bij een onbeperkte bron. Staat "
            "erbij omdat het niet meer per se een invoer is: komt het uit de "
            "droogtestatistiek, dan hangt het aan de gekozen herhaaltijd en is `theta` "
            "zonder dit getal niet terug te rekenen"
        ),
    )
    total_demand_m3: float = Field(
        ..., description="De som van de watervraag over de selectie [m3]"
    )
    total_granted_m3: float = Field(..., description="Wat er is toegewezen [m3]")
    total_shortfall_m3: float = Field(..., description="Wat er onvervuld blijft [m3]")
    theta: float | None = Field(
        None,
        description=(
            "Het gegeven aanbod als fractie van de totale vraag; null bij een onbeperkte "
            "bron. Dit is de as waarop de trap staat"
        ),
    )
    coverage_per_category: dict[str, float] = Field(
        ...,
        description=(
            "Dekkingsfractie per categorie bij het gegeven aanbod. Sleutel is de categorie "
            "als tekst. Dit getal hangt NIET af van hoe er binnen een categorie wordt "
            "verdeeld: elke vorm vult tot de bron of een keel klemt, dus ze verdelen "
            "dezelfde hoeveelheid anders. Hoeveel water er omgaat is dus een modeluitkomst; "
            "wie het krijgt is een beleidskeuze, en die staat in "
            "`individual_coverage_range_per_category`"
        ),
    )
    individual_coverage_range_per_category: dict[str, list[float]] = Field(
        default_factory=dict,
        description=(
            "Per categorie de laagste en hoogste dekking van een INDIVIDUELE afnemer, over "
            "de twee verdedigbare verdelingen binnen een schil. Gelijk tekort geeft iedereen "
            "dezelfde fractie; maximin geeft iedereen hetzelfde volume en legt het tekort "
            "dus bij de grootste vrager. De wet kiest geen van beide - hij noemt "
            "schademinimalisatie - dus dit is de band waarbinnen het antwoord ligt en geen "
            "van de twee is HET antwoord"
        ),
    )
    binding_category: int | None = Field(
        None,
        description=(
            "De laagste categorie die niet volledig gedekt is. Dit is het antwoord op "
            "'wie valt af'; null betekent dat de hele vraag rond komt"
        ),
    )
    binding_is_capacity_not_availability: bool = Field(
        ...,
        description=(
            "True als het tekort door de INLATEN komt en niet door de bron. Dat is een "
            "ander advies: meer water aanvoeren helpt dan niet, een grotere inlaat wel"
        ),
    )
    theta_steps: list[ThetaStep] = Field(
        default_factory=list,
        description=(
            "De droogtetrap: bij welk aanbod welke categorie afvalt. De knikpunten zijn "
            "exact en niet gesampled - ze volgen uit waar een keel verzadigt. Lees een "
            "trede altijd als een BEREIK: de dekking loopt lineair van `coverage_at_low` "
            "naar `coverage_at_high`, dus geen van beide getallen is het antwoord bij het "
            "opgegeven aanbod. Dat antwoord staat in `coverage_per_category`, en de trede "
            "waar het in valt is gemarkeerd met `contains_current_theta`"
        ),
    )

    @model_serializer(mode="wrap")
    def _round_output(self, handler):
        """Rond de hele uitvoer af op significante cijfers; zie SIGNIFICANT_DIGITS.

        Stond hier niet, terwijl de cascade, de maatregeltools en de aanvoertools hem alle
        drie wel hebben. Deze tool gaf dus `total_granted_m3: 3888000.0000000005` en
        `total_shortfall_m3: 911999.9999999995` - drijvende-komma ruis in een veld dat een
        beller letterlijk kan doorgeven, en in dezelfde uitvoer waar `theta` netjes op vier
        cijfers staat.
        """
        return round_floats(handler(self))
