"""Trends: langzame drivers die de toestand tussen twee beslissingen verschuiven.

De derde van de drie soorten exogene processen, en de enige zonder implementatie.

**Waarom dit een eigen soort is.** Een bui en een tekort zijn gebeurtenissen: de transitie
rekent er binnen door, en na afloop is de polder weer wat hij was. Zeespiegelstijging,
bodemdaling en veranderend landgebruik doen iets anders - ze verschuiven `S` zelf, over
jaren, tussen het moment waarop je een maatregel kiest en het moment waarop hij er staat.
Een gebeurtenis kan dat niet dragen: die heeft een duur waar iets binnen gebeurt, en een
trend heeft een tempo waarmee iets wegzakt.

**Dit is de forcering die `γ` nodig heeft.** Disconteren gaat over wanneer je bouwt, en die
vraag bestaat alleen als er iets verandert terwijl je wacht. Zonder trends is er geen
verschil tussen "wat bouw je" en "wanneer bouw je het"; zie `core/reward.py`.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Trend(Protocol):
    """Een langzame driver die de toestand over de jaren verschuift.

    Een protocol zonder implementatie is een plek en geen abstractie: wie de eerste trend
    bouwt, vult hier de vorm in in plaats van ernaast.

    De vorm die we verwachten is `apply_over(state, years) -> PolderState`: de toestand
    zoals hij er na die periode bij staat, zonder maatregel. Dat maakt hem samen te stellen
    met `Action.apply`, en dus bruikbaar in een pad - eerst de trend, dan de maatregel, dan
    de gebeurtenis.
    """

    @property
    def name(self) -> str:
        """Hoe deze trend heet in een antwoord."""
        ...
