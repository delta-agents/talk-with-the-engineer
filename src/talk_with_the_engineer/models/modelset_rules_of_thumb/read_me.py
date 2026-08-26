"""In- en uitvoer van de handleiding-tool."""

from typing import Literal

from pydantic import ConfigDict, Field

from talk_with_the_engineer.models.base import EngineerOutputModel, StringTolerantInput
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    hide_null_branch,
)

MODULES = ("bronnen", "vuistregels", "gebruik", "terugkoppelen")
"""De onderdelen van de handleiding. Hier en niet bij de inhoud, zodat de tool van het model
afhangt en niet andersom - dezelfde richting als de rest van de codebase."""

Module = Literal["bronnen", "vuistregels", "gebruik", "terugkoppelen"]


class ReadMeInput(StringTolerantInput):
    """Welke delen van de handleiding je wilt lezen.

    Bewust geen `language`: de handleiding bestaat alleen in het Nederlands, en een veld dat
    wordt geaccepteerd maar genegeerd is erger dan geen veld.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": {"modules": ["terugkoppelen"]}}
    )

    modules: list[Module] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Welke onderdelen je wilt: 'bronnen' voor de herkomst van de getallen, "
            "'vuistregels' voor wat het model ermee doet en welke aannames de uitkomst "
            "sturen, 'gebruik' voor welke tool bij welke vraag hoort, en 'terugkoppelen' "
            "voor hoe je over het antwoord praat. Laat weg voor een korte index van wat er "
            "te halen valt; vraag er meerdere tegelijk op als je ze allebei nodig hebt"
        ),
    )


class ReadMeOutput(EngineerOutputModel):
    """De gevraagde tekst, plus wat er nog meer te halen valt."""

    text: str = Field(
        ...,
        description=(
            "De handleiding voor de gevraagde onderdelen, als markdown. Dit is uitleg voor "
            "JOU als aanroeper en geen antwoord voor de gebruiker: gebruik het om de juiste "
            "tool te kiezen, om te weten waarop een uitkomst rust, en om er in de juiste "
            "woorden over te praten"
        ),
    )
    available_modules: list[str] = Field(
        default_factory=lambda: list(MODULES),
        description="Alle onderdelen die opgevraagd kunnen worden",
    )
