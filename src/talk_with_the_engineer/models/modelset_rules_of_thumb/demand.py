"""De vraagkant: welke watervraagposten er zijn, en welke daarvan dit model rekent.

De werkopgave 2025 van het Deltaprogramma Zoetwater onderscheidt vier posten in de
zomerse watervraag. Dit model rekent er een:

| post | aandeel NL | aandeel West | zit in dit model |
|---|---|---|---|
| doorspoeling boezem | 23 % | 40 % | nee |
| doorspoeling polders | 9 % | 7 % | nee |
| peilbeheer | 55 % | 46 % | deels |
| beregening | 13 % | 7 % | ja |

`deficit_mm_per_day` is een verdampingstekort dat uit het oppervlaktewater wordt gedekt, en
dat is **beregening**. Van peilbeheer zit het deel erin dat het open water verdampt;
doorspoeling zit er helemaal niet in. Wie een antwoord van deze toolset naast een
werkopgave-getal legt, vergelijkt dus geen twee metingen van hetzelfde.

`DemandPostsInput` maakt die verhouding opvraagbaar per regio, zodat een antwoord kan zeggen
welk deel van de regionale vraag het beslaat, en zodat de verdelingstool de posten naast
elkaar kan zetten met elk hun eigen categorie uit de verdringingsreeks.

De keuze staat op een EIGEN as en niet op de droogte-as. De werkopgave rust op de
Basisprognoses 2018 en daarmee op KNMI'14; de droogtestatistiek hier rust op KNMI'23. Het
cumulatief neerslagtekort onder KNMI'23 gedeeld door dat onder KNMI'14 loopt van 0,94 tot
1,42 en valt juist bij T5 en T10 hoger uit - precies het bereik dat de werkopgave dekt.
`drought_scenario` naar `S2050` vertalen zou twee klimaatproducten gelijkstellen.

De constantenlijsten staan hier en niet als import uit `utils_demand`, om dezelfde reden als
bij de droogte-as: dat bestand woont in het toolpakket en zou een importcykel opleveren. De
WAARDEN komen bij het valideren wel uit het databestand.
"""

from typing import Literal

from pydantic import Field, PrivateAttr, model_validator

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    AssumedDefaults,
    hide_null_branch,
)

DEMAND_REGIONS = (
    "Hoge_Zandgronden_Midden",
    "Hoge_Zandgronden_Noord",
    "Hoge_Zandgronden_Oost",
    "Hoge_Zandgronden_Oost_met_aanvoer",
    "Hoge_Zandgronden_Oost_zonder_aanvoer",
    "Hoge_Zandgronden_Zuid",
    "Hoge_Zandgronden_Zuid_met_aanvoer",
    "Hoge_Zandgronden_Zuid_zonder_aanvoer",
    "Nederland",
    "Noord",
    "Noord_Aanvoergebied_na_Gaarkeuken",
    "Noord_Aanvoergebied_voor_Gaarkeuken",
    "Noord_Drenths_plateau",
    "Noord_Holland_Noord",
    "Noord_IJsselmeerpolders",
    "Noord_Veenkolonien",
    "Rivierengebied",
    "Rivierengebied_Noord",
    "Rivierengebied_Zuid",
    "West",
    "West_Maasdelta",
    "West_met_bovenregionale_aanvoer",
    "West_zonder_bovenregionale_aanvoer",
    "Zuid_Limburg",
    "Zuidwestelijke_Delta",
    "Zuidwestelijke_Delta_met_aanvoer",
    "Zuidwestelijke_Delta_zonder_aanvoer",
)
"""De zes hoofdregio's, de 21 deelregio's op een na, en Nederland als som.

Dit zijn de zoetwaterregio's van het Deltaprogramma Zoetwater, vanaf 2023 gelijkgetrokken met
de bestuurlijke indeling en samenvallend met de zes RDO-regio's. Ze lopen dus NIET gelijk met
de 21 waterschappen van de droogtestatistiek. De Waddeneilanden (S13) ontbreken in de bron.

`test_vraagposten.py` legt naast elkaar dat deze lijst en het databestand hetzelfde zeggen.
"""

DEMAND_SCENARIOS = ("REF2017", "S2050", "S2100")
"""De scenario's van de werkopgave.

`S2050` en `S2100` zijn het Stoom-scenario uit de Deltascenario's, in 2024 hernoemd naar
Stoom, Vlug, Ruim en Warm. Dit zijn niet de KNMI'23-scenario's van de droogtestatistiek.
"""

DEMAND_RETURN_PERIODS = (2, 5, 10, 20)
"""De herhaaltijden van de werkopgave; T20 is de bovengrens.

Dat is geen keuze van ons. De frequentiecurve is per regio afgeleid van het TOTALE
watertekort, en per herhaaltijd zijn de vier jaren met de dichtstbijzijnde herhaaltijd
gemiddeld. Verder gaan dan T20 vraagt een andere methode en niet een extrapolatie.
"""

DEMAND_POSTS = (
    "doorspoeling_boezem",
    "doorspoeling_polders",
    "peilbeheer",
    "beregening",
)
"""De vier posten. `doorspoeling` als geheel is de som van de eerste twee."""

DEMAND_POST_CATEGORY = {
    "peilbeheer": 1,
    "doorspoeling_boezem": 1,
    "doorspoeling_polders": 4,
    "beregening": 4,
}
"""Welke categorie van de verdringingsreeks bij een post hoort (art. 3.14 Bkl).

Het criterium van categorie 1 is veiligheid en ONOMKEERBARE schade, en dat is wat de indeling
hier bepaalt:

* **peilbeheer** is 1. Een uitdrogende waterkering wordt minder stabiel, en klink, zetting en
  veenoxidatie zijn onomkeerbaar. In de zomer van 2026 hebben twee westelijke waterschappen
  bergingsgebieden gevuld voor precies dit doel en de landbouw daarvoor gerantsoeneerd;
* **doorspoeling van de boezem** is 1 voor zover hij zoutindringing tegenhoudt: verzilting van
  een veenpakket is onomkeerbaar. Dient de doorspoeling de waterkwaliteit van een gebruiker -
  glastuinbouw, industrie - dan is het 3 of 4, en dan hoort de beller de categorie zelf op te
  geven;
* **doorspoeling van de polders** is 4: waterkwaliteit voor de functies in de polder, af te
  wegen op economische en maatschappelijke schade;
* **beregening** is 4. Bij kapitaalintensieve gewassen is het 3, en dat is een keuze over dit
  gebied die de beller maakt.

Dit is dus een verdedigbare toewijzing en geen wettelijke tabel: de wet noemt criteria en geen
posten. Zodra de beller `category` zelf opgeeft, wint die.
"""


class DemandPostsInput(AssumedDefaults):
    """De keuze van een vraagverdeling uit de werkopgave: regio, scenario, herhaaltijd.

    Alle drie of geen van drie, net als bij de droogte-as. Laat je ze weg, dan verandert er
    niets aan het antwoord: de verdeling is context en geen forcering.
    """

    demand_region: Literal[*DEMAND_REGIONS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "De zoetwaterregio van het Deltaprogramma Zoetwater waarvan je de "
            "vraagverdeling ophaalt. Dit is een ANDERE indeling dan `drought_region`: dat "
            "zijn de 21 waterschappen van de droogtestatistiek, dit zijn de zes "
            "zoetwaterregio's plus hun deelregio's. Kies de regio waarin je gebied ligt - "
            "'West' dekt Delfland, Rijnland, Schieland en de Krimpenerwaard, De Stichtse "
            "Rijnlanden, Amstel Gooi en Vecht en Hollandse Delta. Gebruik dit veld samen "
            "met `demand_scenario` en `demand_return_period`."
        ),
    )
    demand_scenario: Literal[*DEMAND_SCENARIOS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Het scenario van de werkopgave: 'REF2017' is de referentie, 'S2050' en "
            "'S2100' zijn het Stoom-scenario. Dit zijn NIET de KNMI'23-scenario's van "
            "`drought_scenario`: de werkopgave rust op de Basisprognoses 2018 en daarmee op "
            "KNMI'14, en die onderschat het neerslagtekort ten opzichte van KNMI'23 met een "
            "factor tot 1,42."
        ),
    )
    demand_return_period: Literal[*DEMAND_RETURN_PERIODS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "De herhaaltijd van de werkopgave in jaren. Loopt tot 20 en niet verder: de "
            "frequentiecurve is afgeleid uit de jaren van de reeks zelf en T20 is de "
            "bovengrens die die reeks draagt. Vraag je een hogere op, dan weigert de tool - "
            "doortrekken naar T50 of T100 vraagt een andere methode en niet een "
            "extrapolatie. De herhaaltijd hoort bij het TOTALE watertekort en niet bij de "
            "losse post."
        ),
    )

    _demand_posts = PrivateAttr(default=None)
    """De opgezochte vraagverdeling, of `None` als de beller er niet om vroeg."""

    @property
    def demand_post_choice(self) -> dict:
        """De ingevulde velden van het vraagpost-tripel; leeg als de beller het niet gebruikt."""
        return {
            name: value
            for name in ("demand_region", "demand_scenario", "demand_return_period")
            if (value := getattr(self, name)) is not None
        }

    @property
    def demand_posts(self):
        """De opgezochte verdeling (aandelen, dekking, tekortverdeling), of `None`."""
        return self._demand_posts

    @model_validator(mode="after")
    def resolve_demand_posts(self):
        """Zoek de vraagverdeling op, of leg uit waarom dat niet kan."""
        from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_demand import (
            demand_posts,
        )

        chosen = self.demand_post_choice
        if not chosen:
            return self
        missing = sorted(
            {"demand_region", "demand_scenario", "demand_return_period"} - set(chosen)
        )
        if missing:
            raise ModelRetry(
                "Een vraagverdeling uit de werkopgave vraagt alle drie de velden; deze "
                f"ontbreken: {', '.join(missing)}. Laat ze anders alle drie weg; de "
                "verdeling is context en zonder haar rekent de tool gewoon door."
            )
        found = demand_posts(
            self.demand_region, self.demand_scenario, self.demand_return_period
        )
        if found is None:
            raise ModelRetry(
                f"In {self.demand_region!r} is er in scenario {self.demand_scenario!r} bij "
                f"een herhaaltijd van {self.demand_return_period} jaar geen watervraag "
                "volgens de werkopgave, en dus ook geen verdeling over posten. Kies een "
                "hogere herhaaltijd of de bovenliggende regio."
            )
        self._demand_posts = found
        return self
