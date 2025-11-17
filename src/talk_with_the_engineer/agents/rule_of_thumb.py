"""
First Agent.

This module defines the agent that can answer questions about ...
"""

import os
from pydantic_ai import Agent, Tool
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.agent import AgentRunResult

from talk_with_the_engineer.models.base import Deps

# Import logging utilities from the dedicated module
from talk_with_the_engineer.utils.logging_utils import logger, setup_logging

from talk_with_the_engineer.tools import (
    calculate_retention_given_h,
    calculate_retention_given_area,
)

from talk_with_the_engineer.utils.utils import connect_to_database

from talk_with_the_engineer.models.base import AgentResponse


class RulesOfThumb:
    """
    Talk with the engineer - rules of thumb

    Quick rules used to design by

    Args:
        db_path: Path to the SQLite database
        model: Optional model to use (defaults to PRIMARY_MODEL env var or gpt-4)
        api_key: Optional API key (will use OPENROUTER_API_KEY env var if not provided)
        base_url: Optional base URL (will use OPENROUTER_BASE_URL env var if not provided)
        log_level: Logging level (default is INFO)
        log_dir: Directory where log files will be stored (default is /logs)
    """

    def __init__(
        self,
        db_path: str,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        log_level: str = "INFO",
        log_dir: str = None,
    ):
        self.db_path = db_path

        # Read model name from PRIMARY_MODEL env var if available
        primary_model = os.environ.get("PRIMARY_MODEL")
        default_model = "gpt-4"

        if primary_model:
            logger.info(f"Using model from PRIMARY_MODEL env: {primary_model}")
            default_model = primary_model

        self.model_name = model or default_model
        self.api_key = api_key
        self.base_url = base_url
        self.agent = None
        self.db_connection = None

        # Set up logging
        setup_logging(log_level=log_level, log_dir=log_dir)

        logger.info(f"Initialized Talk with the engineer with database: {db_path}")
        logger.info(f"Using model: {self.model_name}")
        if log_dir:
            logger.info(f"Logging to directory: {log_dir}")

    def __enter__(self):
        """Connect to database and create agent when entering context manager."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close database connection when exiting context manager."""
        self.close()

    def connect(self):
        """Connect to the database and create the agent."""
        if self.db_connection is None:
            logger.info(f"Connecting to database: {self.db_path}")
            self.db_connection = connect_to_database(self.db_path)

            # Create the agent
            self._create_agent()

        return self

    def close(self):
        """Close the database connection."""
        if self.db_connection is not None:
            logger.info("Closing database connection")
            self.db_connection.close()
            self.db_connection = None

    def _create_agent(self):
        """Create the Talk with the engineer with tools."""
        if self.agent is not None:
            return

        db_path = self.db_path
        db_connection = self.db_connection

        if not db_connection:
            logger.warning("Database connection not established. Connecting now.")
            db_connection = connect_to_database(db_path)
            self.db_connection = db_connection

        # Set up dependencies for the agent
        deps = Deps(db_path=db_path, db_connection=db_connection)

        # Extract the database schema for the LLM
        logger.info("Extracting LLM-friendly schema information")

        # Set schema in deps for tools to access

        # Create a simplified system prompt with the schema information
        system_prompt = "You are the Talk with the engineer .... "

        logger.info("Using comprehensive schema from schema_utils")
        # Set up the tools
        tools = [
            Tool(
                calculate_retention_given_h,
                takes_ctx=True,
                name="retention_given_h_tool",
                description="Retention tool - calculate change in retention capacity given change inwater level",
            ),
            Tool(
                calculate_retention_given_area,
                takes_ctx=True,
                name="retention_given_area_tool",
                description="Retention tool - calculate change in water level change given change in retention area",
            ),
        ]

        # Create the model with OpenRouter configuration
        api_key = self.api_key or os.environ.get("OPENROUTER_API_KEY")
        base_url = self.base_url or os.environ.get("OPENROUTER_BASE_URL")

        if not api_key:
            raise ValueError(
                "API key not provided. Either pass as api_key parameter or set OPENROUTER_API_KEY environment variable."
            )

        if not base_url:
            logger.warning(
                "No base_url provided. Using OpenAI API directly. Set OPENROUTER_BASE_URL for custom API."
            )

        # Update to match the template structure
        model = OpenAIModel(
            model_name=self.model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )

        # Create the agent
        logger.info(f"Creating Talk with the engineer using {self.model_name}")
        if base_url:
            logger.info(f"Using custom base URL: {base_url}")

        self.agent = Agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            deps_type=Deps,
            output_type=AgentResponse,
        )

        # Store deps for later use when calling the agent
        self.deps = deps

        return self

    async def ask(self, question: str) -> "AgentRunResult":
        """
        Ask the Talk with the engineer a question.

        Args:
            question: The question to ask

        Returns:
            AgentRunResult: The agent's response object containing AgentResponse in its data property
        """
        if self.agent is None:
            self.connect()

        logger.info(f"Asking agent: {question}")

        try:
            # Use basic run method
            response = await self.agent.run(question, deps=self.deps)
            return response

        except Exception as e:
            logger.error(f"Error asking agent: {str(e)}")
            raise
