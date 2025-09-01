"""
Base models for the Skip the engineer.

This module defines the base models used by the agent to query and analyze
"""

import ast
import json
import sqlite3
from typing import Any, Optional
from pydantic import BaseModel, Field
import duckdb


class EngineerBaseModel(BaseModel):
    """
    Base model that supports flexible input formats including strings.

    Inherit from this class to get automatic string-to-dict conversion support.
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
    Dependencies for the Skip the engineer.

    Attributes:
    """

    def __init__(
        self,
    ):
        pass
