"""De bodem als tweede voorraad: hoeveel er in zit, en hoe snel het bij het gewas komt.

De enige voorraad die dit model kent is de berging onder streefpeil in het open water. Bij
30 cm bruikbare diepte en 3,5 % open water is dat 10,5 mm, en bij een tekort van 4 mm/dag nog
geen drie dagen. De bodem
houdt meer vast, maar niet onmiddellijk beschikbaar - en dat tweede is waar het om gaat.

**Twee getallen, en geen procesmodel.** Dezelfde keuze als op de natte kant, waar de
neerslag-afvoerrelatie een tabel met drie curves is en geen infiltratiemodel: de fysica is één
keer doorgerekend en het resultaat is een tabel.

| grootheid | wat het is |
|---|---|
| voorraad [mm] | wat de bodem geeft en wat niet wordt aangevuld; komt naast `buffer_mm` |
| plafond [mm/dag] | hoe snel water bij het gewas kan komen |

Het plafond is de traagste van twee schakels, en welke dat is verschilt per gebied:

    plafond = min( sloot -> bodem      (opbolling / infiltratieweerstand),
                   bodem -> wortelzone (capillair, ongeveer 2 mm/dag) )

Een derde parameter is niet nodig, want de tijd volgt uit de twee: de voorraad gedeeld door
het plafond is hoe lang hij meegaat. In veen is dat ruim een week, op zandgrond anderhalve
maand.

**En daarom splitst het antwoord in twee regimes.** Met aanvoer is de bodem geen voorraad maar
een doorgeefluik - de sloot vult hem sneller bij dan het gewas hem leegtrekt - en dan telt het
plafond. Zonder aanvoer is het geleverde exact de voorraad, en dan telt hoeveel er in zit. Dat
zijn twee verschillende adviezen: knelt het plafond, dan helpt onderwaterdrainage en een
grotere inlaat niet; knelt de voorraad, dan helpt alleen water van buiten.

De getallen in `SOIL_TYPES` zijn indicatief. Ze komen uit een doorrekening met de aannames die
elke rij bij zich draagt en niet uit een gepubliceerde tabel; een echte tabel hoort uit
LHM/MetaSWAP of Waterwijzer Landbouw te komen, met een bron per rij. Zolang die er niet is
staat dat in een caveat.
"""

from dataclasses import dataclass
from typing import Literal

CAPILLARY_LIMIT_MM_PER_DAY = 2.0
"""Wat capillaire opstijging naar de wortelzone maximaal levert [mm/dag].

De vakterm is de kritieke opstijghoogte: de afstand tussen grondwaterstand en onderkant
wortelzone waarbij het profiel nog een stationaire flux van 2 mm/dag kan leveren. Die afstand
loopt van ongeveer 150 cm in sterk lemig fijn zand tot 50 cm in matig zware klei.

Dit is de schakel die een grondwatervoorraad begrenst juist wanneer je hem nodig hebt: hoe
dieper de stand zakt, hoe minder er capillair naar boven komt. Hier staat hij als constante,
en dat maakt het antwoord aan het eind van een lange droogte te gunstig.
"""

SOIL_LINKS = (
    "sloot_naar_bodem",
    "bodem_naar_wortelzone",
    "wortelzone_naar_gewas",
    "plafond_opgegeven",
    "voorraad_op",
    "bron_leeg",
    "inlaat",
)
"""De schakels tussen de bron en de wortelzone, in de taal waarin `binding_link` antwoordt.

De eerste vier zijn een PLAFOND: er past niet meer per dag doorheen, en een grotere inlaat
verandert daar niets aan; `plafond_opgegeven` staat er zodra de beller het plafond zelf opgaf
en wij dus niet weten welke schakel erachter zit. De laatste drie zijn een HOEVEELHEID: er is
niet meer, en dan helpt alleen water van buiten of een grotere inlaat.
"""


@dataclass(frozen=True)
class SoilType:
    """Eén gebiedstype: wat de bodem geeft, hoe snel, en waarop dat rust.

    De aannames staan erbij en niet alleen het resultaat, zodat elke rij na te rekenen is.
    `store_mm` en de limieten gelden over het LANDoppervlak; de tool rekent ze om naar mm
    over de polder, net als `buffer_mm`.
    """

    store_mm: float
    """De voorraad die de toegestane zakking vrijmaakt [mm over land]."""
    limits: dict
    """Per schakel wat er maximaal per dag door kan [mm/dag over land]."""
    storage_coefficient: float | None
    """De bergingscoefficient waarmee de voorraad is uitgerekend; `None` als hij uit de wortelzone komt."""
    drawdown_m: float | None
    """De grondwaterstandsdaling waarover die voorraad is gerekend [m]."""
    infiltration_resistance_days: float | None
    """De weerstand tussen sloot en bodem [dagen]; `None` als er geen slootinvloed is."""
    what_it_is: str
    """Waar dit type voor staat, in de taal van een beheerder."""

    @property
    def transfer_mm_per_day(self) -> float:
        """Het plafond: de traagste schakel [mm/dag over land]."""
        return min(self.limits.values())

    @property
    def binding_link(self) -> str:
        """De schakel die het plafond zet."""
        return min(self.limits, key=self.limits.get)


SOIL_TYPES = {
    "veenweide": SoilType(
        store_mm=6.0,
        limits={
            "sloot_naar_bodem": 0.67,
            "bodem_naar_wortelzone": CAPILLARY_LIMIT_MM_PER_DAY,
        },
        storage_coefficient=0.03,
        drawdown_m=0.20,
        infiltration_resistance_days=300.0,
        what_it_is=(
            "veenweide met een grondwaterstand van 40 tot 60 cm onder maaiveld. De "
            "stuurbare marge is enkele decimeters: de drooglegging wordt op 60 cm gehouden "
            "omdat dieper nutrientenuitspoeling geeft, en zakking is hier onomkeerbaar. De "
            "infiltratieweerstand is in veen van de orde van honderden dagen, dus de zomerse "
            "aanvoer vanuit de sloot is zeer beperkt"
        ),
    ),
    "kleipolder": SoilType(
        store_mm=15.0,
        limits={
            "sloot_naar_bodem": 1.5,
            "bodem_naar_wortelzone": CAPILLARY_LIMIT_MM_PER_DAY,
        },
        storage_coefficient=0.05,
        drawdown_m=0.30,
        infiltration_resistance_days=200.0,
        what_it_is=(
            "kleipolder met ondiep grondwater. De voorraad is van dezelfde orde als de "
            "open-waterbuffer die het model al kent, en het plafond ligt net op de vraag die "
            "de droogtestatistiek voor laag Nederland geeft"
        ),
    ),
    "zandgrond_met_slootinvloed": SoilType(
        store_mm=60.0,
        limits={
            "sloot_naar_bodem": 5.0,
            "bodem_naar_wortelzone": CAPILLARY_LIMIT_MM_PER_DAY,
        },
        storage_coefficient=0.12,
        drawdown_m=0.50,
        infiltration_resistance_days=100.0,
        what_it_is=(
            "zandgrond binnen bereik van een watergang. Hier is de bodem niet de klem: de "
            "sloot levert ruim, en wat begrenst is de capillaire opstijging naar de "
            "wortelzone"
        ),
    ),
    "zandgrond_zonder_slootinvloed": SoilType(
        store_mm=90.0,
        limits={"bodem_naar_wortelzone": CAPILLARY_LIMIT_MM_PER_DAY},
        storage_coefficient=0.15,
        drawdown_m=0.60,
        infiltration_resistance_days=None,
        what_it_is=(
            "zandgrond met diep grondwater en zonder aanvoer. De voorraad is hier een orde "
            "groter dan de open-waterbuffer, en dat is het enige gebiedstype waarvoor dat "
            "geldt. Wat er niet is, is aanvoer: op de hoge zandgronden is beschikbaarheid en "
            "niet capaciteit de bindende beperking"
        ),
    ),
    "droogtegevoelig_zand": SoilType(
        store_mm=45.0,
        limits={"wortelzone_naar_gewas": 4.0},
        storage_coefficient=None,
        drawdown_m=None,
        infiltration_resistance_days=None,
        what_it_is=(
            "zandgrond waar het grondwater buiten capillair bereik staat. Dan draagt de "
            "wortelzone zelf de hele voorraad, hij gaat er snel uit, en daarna is er niets "
            "meer. Dit is het enige type waar het plafond boven de capillaire grens ligt, "
            "want het water komt niet van beneden"
        ),
    ),
}
"""De vijf gebiedstypen, van de kleinste voorraad naar de grootste.

De winst zit op de zandgronden en niet in het westen: in het Groene Hart is de bodemvoorraad
kleiner dan de open-waterbuffer die het model al heeft. Dat is de omgekeerde uitkomst van wat
je zou verwachten van een grondwatervoorraad, en het is de reden dat dit een gebiedstype is en
geen landelijke correctie.
"""

SOIL_TYPE_NAMES = tuple(SOIL_TYPES)

SoilTypeName = Literal[*SOIL_TYPE_NAMES]


def soil_type_summary() -> str:
    """De tabel als regel per type, voor de handleiding en de veldbeschrijving."""
    return "\n".join(
        f"- `{name}`: {body.store_mm:g} mm voorraad, plafond "
        f"{body.transfer_mm_per_day:g} mm/dag ({body.binding_link})"
        for name, body in SOIL_TYPES.items()
    )


@dataclass(frozen=True)
class SoilRelease:
    """Wat de bodem van DIT gebied geeft, en hoe snel.

    De twee getallen die de droge transitie uit een gebiedstype nodig heeft, over het
    LANDoppervlak. `SoilType` hierboven is de catalogusrij met zijn hele onderbouwing; dit
    is wat er van overblijft zodra je een gebied kiest.

    Geen van drie heeft een standaardwaarde die "een beetje bodem" betekent: zonder
    gebiedstype is de voorraad alleen het open water, en dan is het antwoord wat het zonder
    bodem is.
    """

    store_mm: float
    """Wat de bodem geeft en wat niet wordt aangevuld [mm over land]."""
    transfer_mm_per_day: float
    """Hoe snel water bij het gewas kan komen [mm/dag over land]."""
    binding_link: str | None = None
    """Welke schakel het plafond zet; `None` als de beller het plafond zelf opgaf."""

    @property
    def is_modelled(self) -> bool:
        """Of er een bodem meedoet, of dat dit het gedrag zonder bodem is."""
        return self.store_mm > 0.0 or self.transfer_mm_per_day != float("inf")


NO_SOIL = SoilRelease(store_mm=0.0, transfer_mm_per_day=float("inf"))
"""De bodem zoals dit model hem zonder gebiedstype kent: geen voorraad, geen plafond.

Met deze waarden valt de bodemtak weg tot op de bit: een voorraad van nul verdiept de band
niet en een oneindig plafond knijpt de vraag niet af.
"""
