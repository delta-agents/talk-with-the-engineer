"""
Base models for the Talk with the engineer.

This module defines the base models used by the agent to query and analyze
"""

import ast
import json
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


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
