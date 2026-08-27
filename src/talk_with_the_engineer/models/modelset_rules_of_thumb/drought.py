"""De droogte-as: welke droogte, en wat de bron dan te bieden heeft.

Twee mixins die de vraag- en de aanbodkant van dezelfde statistiek dragen, zodat de
eenpolder-aanvoertools en de allocatietool ze allebei kunnen erven in plaats van elk hun
eigen versie te schrijven:

| | vraag | aanbod |
|---|---|---|
| grootheid | maximaal cumulatief neerslagtekort [mm] | minimale 7-daagse rivierafvoer [m3/s] |
| in de tool | `deficit_mm_per_day` maal `length_days` | `available_source_volume_m3` |
| komt uit | `DroughtStatisticInput` (het tripel) | `SourceVolumeInput` (fractie maal normaaljaar) |

Beide lezen hetzelfde bestand op dezelfde as - waterschap, klimaatscenario, herhaaltijd -
en dat is het hele punt van dit bestand. Stond het aanbod los van die as, dan zou een
zeldzamere droogte de vraag verhogen en het aanbod laten staan, en dat is niet een
voorzichtige aanname maar een systematisch te gunstig antwoord.

De constantenlijsten staan hier en niet als import uit `utils_drought`, want dat bestand
woont in het toolpakket en `tools/__init__.py` importeert de tools, die weer de modellen
importeren - een import op moduleniveau zou dus een cykel opleveren. De WAARDEN worden bij
het valideren wel uit het bestand gehaald, met een import binnen de functie;
`test_droogtestatistiek.py` bewaakt dat deze lijsten en het databestand hetzelfde zeggen.
"""

from typing import Literal

from pydantic import Field, PrivateAttr, model_validator

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    AssumedDefaults,
    hide_null_branch,
)

DROUGHT_REGIONS = (
    "Aa_en_Maas",
    "Amstel_Gooi_en_Vecht",
    "Brabantse_Delta",
    "Delfland",
    "Dommel",
    "Drents_Overijsselse_Delta",
    "Fryslan",
    "Hollands_Noorderkwartier",
    "Hollandse_Delta",
    "Hunze_en_Aas",
    "Limburg",
    "Noorderzijlvest",
    "Rijn_en_IJssel",
    "RijnlandWaterschap",
    "Rivierenland",
    "Scheldestromen",
    "Schieland_en_Krimpenerwaard",
    "Stichtse_Rijnlanden",
    "Vallei_en_Veluwe",
    "Vechtstromen",
    "Zuiderzeeland",
)

DROUGHT_SCENARIOS = (
    "Referentie",
    "Hd_2050",
    "Hd_2100",
    "Hn_2050",
    "Hn_2100",
    "Ld_2100",
    "Ln_2100",
)

DROUGHT_RETURN_PERIODS = (2, 5, 10, 25, 50, 100)

SOURCE_RIVERS = ("Maas", "Rijn")
"""De twee rivieren waarvoor de statistiek een aanbod bijhoudt.

Alfabetisch, en dat is geen smaak maar de volgorde waarin `available_rivers()` ze levert;
`test_droogtestatistiek.py` legt naast elkaar dat deze lijst en het bestand hetzelfde zeggen.
"""


class DroughtStatisticInput(AssumedDefaults):
    """De keuze van een droogte uit STOWA 2025-23: waterschap, scenario, herhaaltijd.

    Alle drie of geen van drie. Wat er met die keuze gebeurt verschilt per tool - de
    aanvoertools halen er een neerslagtekort uit, de allocatietool een bronvolume - maar de
    keuze zelf is dezelfde en hoort dus op een plek te staan.
    """

    drought_region: Literal[*DROUGHT_REGIONS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Het waterschap waarvoor je de droogte uit de statistiek haalt (STOWA 2025-23). "
            "De ruimtelijke variatie in het neerslagtekort is meer dan 30 % tussen noord en "
            "zuid, dus een landelijk gemiddelde is voor de meeste gebieden het verkeerde "
            "getal. Gebruik dit veld samen met `drought_scenario` en "
            "`drought_return_period`."
        ),
    )
    drought_scenario: Literal[*DROUGHT_SCENARIOS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Het klimaatscenario: 'Referentie' is het huidige klimaat (1991-2020), de "
            "andere zijn KNMI'23 met H of L voor de uitstoot, d of n voor droog of nat, en "
            "het zichtjaar erachter. Ter ijking: in Rijn en IJssel is het tekort bij T10 "
            "269 mm in de referentie, 361 mm in Hd_2050 en 451 mm in Hd_2100."
        ),
    )
    drought_return_period: Literal[*DROUGHT_RETURN_PERIODS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "De herhaaltijd van de droogte in jaren. Dit is de droogte-tegenhanger van "
            "`return_period` op de natte kant. Let op: niet elke combinatie bestaat - bij "
            "de natste scenario's is T100 niet bereikt binnen de gebruikte reeks, en dan "
            "weigert de tool met uitleg in plaats van te extrapoleren."
        ),
    )

    @property
    def drought_statistic_choice(self) -> dict:
        """De ingevulde velden van het tripel; leeg als de beller de statistiek niet gebruikt."""
        return {
            name: value
            for name in ("drought_region", "drought_scenario", "drought_return_period")
            if (value := getattr(self, name)) is not None
        }

    @model_validator(mode="after")
    def require_the_whole_triple(self):
        """Half een droogte kiezen bestaat niet.

        Deze regel staat hier en niet bij de tekort-resolutie, omdat hij over de KEUZE gaat
        en niet over wat je ermee doet: ook de allocatietool, die uit hetzelfde tripel een
        bronvolume haalt en geen tekort, heeft hem nodig.
        """
        chosen = self.drought_statistic_choice
        if not chosen:
            return self
        missing = sorted(
            {"drought_region", "drought_scenario", "drought_return_period"}
            - set(chosen)
        )
        if missing:
            raise ModelRetry(
                "Een droogte uit de statistiek vraagt alle drie de velden; deze "
                f"ontbreken: {', '.join(missing)}. Laat ze anders alle drie weg."
            )
        return self


class SourceVolumeInput(DroughtStatisticInput):
    """Wat de bron over deze periode kan leveren - opgegeven, of uit de statistiek.

    Twee wegen naar hetzelfde getal, dezelfde vorm als het neerslagtekort al heeft:

    * `available_source_volume_m3` zelf opgeven, of
    * `source_volume_normal_year_m3` plus `source_river` opgeven en het tripel erbij kiezen;
      dan zoekt de tool op hoeveel minder een bron in een droogte van deze zeldzaamheid
      levert en rekent het volume uit.

    **Waarom een fractie en geen kubieke meters uit de statistiek.** De statistiek kent de
    minimale 7-daagse afvoer van de Rijn en de Maas. Dat is niet het water bij jouw inlaat:
    daartussen zitten het verdeelnetwerk, het Distributiemodel en de verdringingsreeks. Een
    volume uit die afvoer afleiden zou een getal verzinnen. Een fractie laat de lokale kennis
    waar hij hoort - bij de beller, die weet wat zijn bron in een normaal jaar levert - en
    voegt eraan toe wat de statistiek wel weet: hoeveel minder dat wordt naarmate de droogte
    extremer is en het klimaat verder opschuift.
    """

    available_source_volume_m3: float | None = Field(
        None,
        ge=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Wat de bron over deze periode kan leveren [m3]. Laat weg als je dat niet weet - "
            "dan rekent de tool met een onbeperkte bron, en dat is een DRAGENDE aanname: hij "
            "veronderstelt dat het water bij de inlaat staat. Voor laag Nederland is dat "
            "vaak onschuldig, voor de zandgronden niet. Vul hem in en de aanname wordt een "
            "getal: dan staat er vanaf welke dag de inlaat droog staat. Weet je wel wat je "
            "bron in een NORMAAL jaar levert maar niet in een droog jaar, geef dan "
            "`source_volume_normal_year_m3` en `source_river` op en laat dit veld weg; de "
            "tool leest de droogte-afslag dan uit dezelfde statistiek als het neerslagtekort."
        ),
    )
    source_volume_normal_year_m3: float | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Wat de bron over deze periode levert in een NORMAAL jaar [m3]. Samen met "
            "`source_river` en de gekozen droogte leidt de tool hieruit "
            "`available_source_volume_m3` af: hoe zeldzamer de droogte en hoe verder het "
            "klimaatscenario, hoe kleiner de fractie die hiervan overblijft. Gebruik dit veld "
            "OF `available_source_volume_m3`, niet allebei."
        ),
    )
    source_river: Literal[*SOURCE_RIVERS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "De rivier die de bron voedt, en dus de rivier waarvan de droogte-afslag wordt "
            "afgelezen. Hoort bij `source_volume_normal_year_m3`. De twee lopen niet gelijk: "
            "de Maas is een regenrivier en zakt in een droogte verder terug dan de Rijn, die "
            "smeltwater meekrijgt."
        ),
    )

    _source_availability = PrivateAttr(default=None)
    """De opgezochte beschikbaarheid, of `None` als de beller het volume zelf opgaf.

    Een privéveld en geen gewoon veld, om dezelfde reden als `_assumed_fields`: het is een
    UITKOMST van het valideren en hoort in de uitvoer thuis, niet in het invoerschema.
    """

    @property
    def source_availability(self):
        """De opgezochte beschikbaarheid (fractie, spreiding, sterkte van het verband).

        `None` wanneer de beller het bronvolume zelf opgaf of helemaal weglaat; dan is er
        niets opgezocht.
        """
        return self._source_availability

    @model_validator(mode="after")
    def resolve_source_volume(self):
        """Zet de gekozen droogte om in een bronvolume, of leg uit waarom dat niet kan."""
        from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
            source_availability,
        )

        wants_derived = (
            self.source_volume_normal_year_m3 is not None
            or self.source_river is not None
        )
        if not wants_derived:
            return self

        if self.available_source_volume_m3 is not None:
            raise ModelRetry(
                "Het bronvolume opgeven EN uit de statistiek laten afleiden is dubbelop: "
                f"`available_source_volume_m3`={self.available_source_volume_m3:g} staat "
                "naast een normaaljaar-volume. Laat een van de twee weg, anders is niet te "
                "zien welk van beide het antwoord stuurt."
            )
        missing = sorted(
            {"source_volume_normal_year_m3", "source_river"}
            - {
                name
                for name in ("source_volume_normal_year_m3", "source_river")
                if getattr(self, name) is not None
            }
        )
        if missing:
            raise ModelRetry(
                "Het bronvolume uit de statistiek vraagt allebei de velden; deze "
                f"ontbreken: {', '.join(missing)}. De rivier bepaalt welke afslag wordt "
                "afgelezen en de Maas zakt in een droogte verder terug dan de Rijn, dus dat "
                "is geen detail."
            )

        chosen = self.drought_statistic_choice
        if not chosen:
            raise ModelRetry(
                "Een bronvolume uit de statistiek vraagt om een droogte uit dezelfde "
                "statistiek: geef `drought_region`, `drought_scenario` en "
                "`drought_return_period` op. Zonder die keuze is er geen droogte waarvan de "
                "afslag kan worden afgelezen; geef anders `available_source_volume_m3` "
                "rechtstreeks op."
            )

        availability = source_availability(
            self.drought_region,
            self.drought_scenario,
            self.drought_return_period,
            self.source_river,
        )
        if availability is None:
            raise ModelRetry(
                f"Voor {self.drought_region!r} in scenario {self.drought_scenario!r} is er "
                f"geen droogte bij een herhaaltijd van {self.drought_return_period} jaar, en "
                "dus ook geen aanbod: die valt buiten de reeks waarop deze statistiek is "
                "gefit. Extrapoleren zou een getal verzinnen waar het rapport er geen heeft."
            )

        self._source_availability = availability
        self.available_source_volume_m3 = (
            self.source_volume_normal_year_m3 * availability.fraction
        )
        return self
