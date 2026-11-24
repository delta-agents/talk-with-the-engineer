"""
Base models for the Talk with the engineer.

This module defines the base models used by the agent to query and analyze
"""

import ast
import json
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, PrivateAttr


LANGUAGE_OPTIONS = ["nl", "en"]


class StringTolerantInput(BaseModel):
    """Invoer die ook als string binnen mag komen, met of zonder `input`-wikkel.

    Los van `EngineerBaseModel` omdat niet elke invoer een TAAL heeft. Een tool die uitleg
    teruggeeft in één taal moet geen `language` adverteren dat hij vervolgens negeert; dat is
    dezelfde faalmodus als een maatregel die wordt geaccepteerd en niets doet.
    """

    @classmethod
    def model_validate(cls, obj: Any, *args, **kwargs):
        """
        Custom validation that can handle string input representing a dict.
        """
        if isinstance(obj, str):
            try:
                # First try to parse as JSON
                parsed = json.loads(obj)
            except json.JSONDecodeError:
                try:
                    # If JSON fails, try to parse as Python literal (handles single quotes)
                    parsed = ast.literal_eval(obj)
                except (ValueError, SyntaxError) as e:
                    raise ValueError(
                        f"Invalid string format. Expected JSON or Python dict literal. Error: {e}"
                    )

            if not isinstance(parsed, dict):
                raise ValueError("String must represent a dictionary")

            # Extract the 'input' key if it exists
            if "input" in parsed:
                parsed = parsed["input"]

            obj = parsed

        return super().model_validate(obj, *args, **kwargs)


class EngineerBaseModel(StringTolerantInput):
    """Invoer van een rekentool: string-tolerant, plus de taal van de uitvoer."""

    language: Literal[*LANGUAGE_OPTIONS] = Field(
        "nl",
        description="Taal van de tooluitvoer: 'nl' voor Nederlands, 'en' voor Engels",
    )


class EngineerOutputModel(BaseModel):
    """Basis voor de UITVOER van een tool.

    Bewust geen `language`, en dat is de hele reden dat deze klasse naast
    `EngineerBaseModel` staat. Die laatste doet twee dingen die alleen bij INVOER horen: hij
    pelt een `input`-sleutel van een string af, en hij draagt het taalveld dat de beller
    meestuurt. Een uitvoermodel dat daarvan erft geeft dat taalveld weer terug - wie 'nl'
    instuurt krijgt 'nl' terug - en dat is een echo zonder informatie, op elke tool.

    Uitvoer wordt door ons geconstrueerd en niet uit een string van een taalmodel geparsed,
    dus de conversie eromheen is hier ook niet nodig.
    """


class AgentResponse(BaseModel):
    """
    Model for standardized agent responses.

    This model provides a consistent structure for all agent responses,
    allowing for text, tables, and diagram content.

    Attributes:
        markdown_text: Primary text response in markdown format
        markdown_table: Optional tabular data in markdown format
        mermaid_diagram: Optional mermaid diagram code
    """

    markdown_text: str = Field(
        ..., description="Primary text response in markdown format"
    )
    markdown_table: Optional[str] = Field(
        None, description="Optional tabular data in markdown format"
    )
    mermaid_diagram: Optional[str] = Field(
        None,
        description="Optional mermaid diagram code, makee sure it uses nodes on a new line",
    )


class ToolCallTracker:
    """Class to track tool calls and their results.

    This class is used to maintain a history of tool calls and their outcomes,
    which can be useful for debugging and analysis.
    """

    def __init__(self):
        self.calls = []


class Deps:
    """
    Dependencies for the Talk with the engineer.

    Attributes:
    """

    def __init__(
        self,
    ):
        pass


# --- De schemamachinerie: fallbacks zonder `default` in het schema ------------------


# --- Standaardwaarden: van het schema naar de tool ----------------------------------
#
# De velden hieronder hebben in het schema geen `default` meer. De waarde staat in
# FIELD_FALLBACKS en wordt door `apply_fallbacks` ingevuld zodra het veld `None` is.
#
# Dat is niet cosmetisch. Een tool die zijn aannames wil melden moet weten welke velden de
# beller heeft weggelaten, en dat is niet af te leiden uit `model_fields_set`: een
# MCP-client mag de standaardwaarden uit het schema in de aanroep invullen voordat hij hem
# verstuurt, en dan is server-side elk veld "opgegeven". Gemeten bij Claude Code: dezelfde
# kale payload gaf via een gewone `fastmcp.Client` zes aannames en via die client nul, bij
# identieke getallen.
#
# Staat er geen `default` in het schema, dan heeft die client niets om in te vullen en komt
# het veld aan zoals de beller het liet: als `None`. Een expliciete `null` werkt ook, maar
# daar valt niet op te bouwen - een client die zijn payload zelf tegen het schema
# valideert wijst hem af, want de null-tak wordt niet geadverteerd; zie `hide_null_branch`.
#
# De prijs is dat de fallbackwaarde niet meer uit het schema te lezen is. Die staat daarom
# in de veldbeschrijving en, voor clients die de beschrijvingen weghalen, in
# `SHARED_FOOTER`.

FIELD_FALLBACKS = {
    "time_of_year": "summer",
    "length_event_hrs": 96.0,
    "rainfall_regime": "R",
    "name_rainfall_pattern": "p1c",
    "days_to_discharge": 3,
    "percentage_open_water": 2.0,
    "days_to_retain_discharge": 2,
    "length_days": 30,
}


def hide_null_branch(schema: dict) -> None:
    """Laat het veld in het schema zien wat het echt aankan, zonder de null-tak.

    Pydantic maakt van `Literal[...] | None` een `anyOf` met een null-tak, en dan zakt de
    `enum` een niveau naar beneden - precies de informatie die een client nodig heeft om
    een geldige waarde te kiezen. Die null-tak is hier geen keuze maar het mechanisme van
    weglaten: null en niets betekenen hetzelfde, en dat hoeft een beller niet te weten.

    `default` gaat er ook uit. Een geadverteerde standaardwaarde is precies wat een client
    in de aanroep invult, en dan is niet meer te zien wat de beller heeft weggelaten.
    """
    branches = schema.pop("anyOf", None)
    if branches:
        real = next(b for b in branches if b.get("type") != "null")
        schema.update(real)
    schema.pop("default", None)


def hide_null_branch_and_bound(minimum: float):
    """`hide_null_branch`, plus een ondergrens die in het schema zichtbaar is.

    Twee dingen die allebei op `json_schema_extra` moeten en dat veld is er een. De
    ondergrens staat bewust NIET als `ge=` op het veld: een pydantic-constraint levert aan
    de MCP-grens een ruwe validatiedump op, met `[type=greater_than_equal]` en een link naar
    errors.pydantic.dev erin. Dezelfde afweging als bij `delta_area_ha`; de handhaving hoort
    in een validator met een melding in de stijl van de rest van dit systeem.
    """

    def apply(schema: dict) -> None:
        hide_null_branch(schema)
        schema["minimum"] = minimum

    return apply


class AssumedDefaults(EngineerBaseModel):
    """Houdt bij welke velden met een fallback zijn ingevuld.

    Een privéveld en geen gewoon veld: het hoort in de uitvoer thuis (`assumptions`), niet
    in het invoerschema, waar het een beller alleen maar zou verleiden het zelf te vullen.
    """

    _assumed_fields: set[str] = PrivateAttr(default_factory=set)

    def apply_fallbacks(self, *names: str) -> None:
        """Vul de weggelaten velden en onthoud welke dat waren."""
        for name in names:
            if getattr(self, name) is None:
                setattr(self, name, FIELD_FALLBACKS[name])
                self._assumed_fields.add(name)

    @property
    def assumed_fields(self) -> set[str]:
        """De velden waarvoor deze aanroep op een fallback leunt."""
        return set(self._assumed_fields)
