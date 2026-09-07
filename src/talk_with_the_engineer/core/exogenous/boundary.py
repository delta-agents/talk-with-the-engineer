"""Randvoorwaarden: wat de buitenwereld tijdens een gebeurtenis levert.

De tweede van de drie soorten exogene processen. Geen gebeurtenis met een duur, maar een
WAARDE aan de rand van het gebied: hoeveel de rivier kan leveren, hoe zout het water bij de
inlaat is, hoe hoog de boezem staat.

**`OUTSIDE` en `BoundaryCondition` horen bij elkaar en zijn niet hetzelfde.** `OUTSIDE` in
`connection.py` zegt WIE er aan de andere kant van een verbinding zit; dat is topologie en
dus toestand. Dit zegt WAT die knoop levert, en dat is exogeen. Vandaar dat ze in twee
mappen staan: een polder houdt zijn buur ook als het niet regent.

Vandaag een veld. Zout, buitenwaterstand en rivierafvoer horen hier, en dan landen ze op
deze plek in plaats van elk met een eigen stille standaardwaarde in de transitie.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundaryCondition:
    """De stand van de buitenwereld tijdens de gebeurtenis.

    `available_source_volume_m3` is wat de bron over de hele periode kan leveren. `inf` is
    onbeperkt, en dat is precies de aanname die de caveat over aanvoerbeschikbaarheid
    benoemt: dat het water bij de inlaat is. Vul hem in en die aanname wordt een getal.

    Een expliciete waarde en geen standaardwaarde binnenin de transitie. Een aanname die op
    twee rekenpaden apart wordt ingevuld, kan op die twee paden uiteenlopen zonder dat het
    aan de uitkomst te zien is; hier staat hij een keer, en op de aanroep is te lezen wie
    hem kiest.
    """

    available_source_volume_m3: float = float("inf")

    @property
    def is_unlimited(self) -> bool:
        """Of de bron over deze periode geen grens stelt."""
        return self.available_source_volume_m3 == float("inf")


UNLIMITED = BoundaryCondition()
"""De rand zoals een model van een losse polder hem stilzwijgend aanneemt: onbeperkt.

Een benoemde constante, zodat een doorrekening zonder bronbeperking dat op de aanroep zegt
in plaats van het weg te laten.
"""
