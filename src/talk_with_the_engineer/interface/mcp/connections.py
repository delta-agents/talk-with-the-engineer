import json
import os
from pathlib import Path
from pydantic_ai import RunContext
from talk_with_the_engineer.interface.schemas.base import Deps
from dotenv import load_dotenv


# see talk-with-fews for user specific configuration of tools
def setup_env():
    """Load environment variables from a .env file located in the 'env' directory."""
    env_dir = Path(__file__).parent.parent.parent.parent / "env"
    load_dotenv(dotenv_path=env_dir / ".env")
    return json.load(
        open(env_dir / os.getenv("STATIC_TOKENS_FILE", ".static_tokens_example.json"))
    )


# def get_user_settings(verifier) -> dict:
### ....


class CtxWithDeps:
    def __init__(self, deps):
        self.deps = deps


def get_runtime_ctx() -> RunContext:
    """
    Returns a RunContext[Deps] with a shared dependencies.
    for now unused.
    Leave in for compatibility later.
    """
    # combine all three into a Deps object
    deps = Deps()
    return CtxWithDeps(deps)
